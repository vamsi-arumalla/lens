package com.lens.app.audio

import android.content.Context
import android.media.MediaRecorder
import android.os.Build
import java.io.File

/** Records mic audio to an m4a (AAC in MPEG-4) file in the cache dir. */
class VoiceRecorder(private val context: Context) {

    private var recorder: MediaRecorder? = null
    private var file: File? = null

    fun start() {
        stopQuietly()
        val out = File(context.cacheDir, "question-${System.currentTimeMillis()}.m4a")
        @Suppress("DEPRECATION")
        val r = if (Build.VERSION.SDK_INT >= 31) MediaRecorder(context) else MediaRecorder()
        r.setAudioSource(MediaRecorder.AudioSource.MIC)
        r.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
        r.setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
        r.setAudioSamplingRate(16000)
        r.setAudioChannels(1)
        r.setOutputFile(out.absolutePath)
        r.prepare()
        r.start()
        recorder = r
        file = out
    }

    /** Returns the recorded file, or null if recording failed/was too short. */
    fun stop(): File? {
        val r = recorder ?: return null
        val out = file
        recorder = null
        file = null
        return try {
            r.stop()
            r.release()
            out?.takeIf { it.length() > 0 }
        } catch (e: RuntimeException) {
            // stop() throws if no valid audio was captured (e.g. instant tap)
            r.release()
            out?.delete()
            null
        }
    }

    private fun stopQuietly() {
        try {
            recorder?.release()
        } catch (_: Exception) {
        }
        recorder = null
        file?.delete()
        file = null
    }
}
