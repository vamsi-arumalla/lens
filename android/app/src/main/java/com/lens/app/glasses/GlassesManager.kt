package com.lens.app.glasses

import android.graphics.BitmapFactory
import android.util.Log
import com.meta.wearable.dat.camera.addStream
import com.meta.wearable.dat.camera.Stream
import com.meta.wearable.dat.camera.types.PhotoData
import com.meta.wearable.dat.camera.types.StreamConfiguration
import com.meta.wearable.dat.camera.types.StreamState
import com.meta.wearable.dat.camera.types.VideoQuality
import com.meta.wearable.dat.core.Wearables
import com.meta.wearable.dat.core.selectors.AutoDeviceSelector
import com.meta.wearable.dat.core.session.DeviceSession
import com.meta.wearable.dat.core.session.DeviceSessionState
import java.io.ByteArrayOutputStream
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeout

enum class GlassesState { DISCONNECTED, CONNECTING, READY, ERROR }

/**
 * Owns the DAT session + camera stream lifecycle. When the stream dies for
 * any reason (glasses folded, Bluetooth lost, mock disabled) the state drops
 * to DISCONNECTED and the ask flow falls back to the phone camera.
 */
class GlassesManager(private val scope: CoroutineScope) {

    private val _state = MutableStateFlow(GlassesState.DISCONNECTED)
    val state: StateFlow<GlassesState> = _state

    private var session: DeviceSession? = null
    private var stream: Stream? = null
    private var watchJob: Job? = null

    suspend fun connect(): Boolean {
        if (_state.value == GlassesState.READY) return true
        _state.value = GlassesState.CONNECTING
        return try {
            val session = Wearables.createSession(AutoDeviceSelector()).getOrThrow()
            this.session = session
            session.start()
            withTimeout(15_000) {
                session.state.first { it == DeviceSessionState.STARTED }
            }
            val stream = session
                .addStream(
                    StreamConfiguration(
                        videoQuality = VideoQuality.MEDIUM,
                        frameRate = 15,
                        compressVideo = false,
                    )
                )
                .getOrThrow()
            this.stream = stream
            stream.start()
            withTimeout(15_000) { stream.state.first { it == StreamState.STREAMING } }
            watchJob = scope.launch {
                stream.state.collect { s ->
                    if (s == StreamState.STOPPED || s == StreamState.CLOSED) disconnect()
                }
            }
            _state.value = GlassesState.READY
            true
        } catch (e: Exception) {
            Log.w("GlassesManager", "glasses connect failed", e)
            disconnect()
            _state.value = GlassesState.ERROR
            false
        }
    }

    fun disconnect() {
        watchJob?.cancel()
        watchJob = null
        runCatching { stream?.stop() }
        runCatching { stream?.close() }
        runCatching { session?.stop() }
        stream = null
        session = null
        _state.value = GlassesState.DISCONNECTED
    }

    /** Capture one still from the glasses stream as contract-conforming JPEG. */
    suspend fun capturePhotoJpeg(): ByteArray {
        val stream = stream ?: error("glasses are not streaming")
        return stream.capturePhoto().getOrThrow().toJpeg()
    }
}

private fun PhotoData.toJpeg(): ByteArray = when (this) {
    is PhotoData.Bitmap ->
        ByteArrayOutputStream().also {
            bitmap.compress(android.graphics.Bitmap.CompressFormat.JPEG, 85, it)
        }.toByteArray()
    is PhotoData.HEIC -> {
        val bytes = ByteArray(data.remaining()).also { data.get(it) }
        val bmp = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
            ?: error("could not decode HEIC photo from glasses")
        ByteArrayOutputStream().also {
            bmp.compress(android.graphics.Bitmap.CompressFormat.JPEG, 85, it)
        }.toByteArray()
    }
    else -> error("unsupported PhotoData variant: ${this::class.simpleName}")
}

/** Process-wide glasses runtime; UI observes [manager.state]. */
object GlassesRuntime {
    val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    val manager = GlassesManager(scope)
}
