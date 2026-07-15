package com.lens.app

import android.app.Application
import androidx.annotation.OptIn
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.media3.common.MediaItem
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi
import androidx.media3.datasource.DataSource
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.source.ProgressiveMediaSource
import com.lens.app.data.LensSettings
import com.lens.app.data.SettingsStore
import com.lens.app.net.LensClient
import com.lens.app.net.StreamingDataSource
import java.io.File
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

enum class AskStatus { IDLE, RECORDING, THINKING, SPEAKING, ERROR }

data class AskUiState(
    val status: AskStatus = AskStatus.IDLE,
    val errorMessage: String? = null,
    val timings: Map<String, String> = emptyMap(),
    val showDebugOverlay: Boolean = false,
)

@OptIn(UnstableApi::class)
class AskViewModel(app: Application) : AndroidViewModel(app) {

    val settingsStore = SettingsStore(app)

    val settings: StateFlow<LensSettings> = settingsStore.settings
        .stateIn(viewModelScope, SharingStarted.Eagerly, LensSettings())

    private val _uiState = MutableStateFlow(AskUiState())
    val uiState: StateFlow<AskUiState> = _uiState

    private val player: ExoPlayer = ExoPlayer.Builder(app).build().apply {
        addListener(object : Player.Listener {
            override fun onPlaybackStateChanged(playbackState: Int) {
                if (playbackState == Player.STATE_ENDED) {
                    _uiState.value = _uiState.value.copy(status = AskStatus.IDLE)
                }
            }

            override fun onIsPlayingChanged(isPlaying: Boolean) {
                if (isPlaying) {
                    _uiState.value = _uiState.value.copy(status = AskStatus.SPEAKING)
                }
            }

            override fun onPlayerError(error: PlaybackException) {
                _uiState.value = _uiState.value.copy(
                    status = AskStatus.ERROR,
                    errorMessage = "Couldn't reach Lens — check the backend URL in settings.",
                )
            }
        })
    }

    fun onRecordingStarted() {
        _uiState.value = _uiState.value.copy(status = AskStatus.RECORDING, errorMessage = null)
    }

    fun cancelToIdle() {
        _uiState.value = _uiState.value.copy(status = AskStatus.IDLE)
    }

    fun toggleDebugOverlay() {
        _uiState.value = _uiState.value.copy(showDebugOverlay = !_uiState.value.showDebugOverlay)
    }

    /** Ship the captured frame + voice question to /ask and stream the spoken answer. */
    fun ask(frameJpeg: ByteArray, audio: File?) {
        if (audio == null) {
            _uiState.value = _uiState.value.copy(
                status = AskStatus.ERROR,
                errorMessage = "Hold the button while you speak.",
            )
            return
        }
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(status = AskStatus.THINKING)
            val request = LensClient.askRequest(settingsStore.current(), frameJpeg, audio)
            val factory = DataSource.Factory {
                StreamingDataSource(LensClient.http, request) { headers ->
                    val stages = headers.entries
                        .firstOrNull { it.key.equals("X-Stage-Timings", ignoreCase = true) }
                        ?.value.orEmpty()
                        .split(",")
                        .mapNotNull { part ->
                            part.split("=").takeIf { it.size == 2 }?.let { it[0] to it[1] }
                        }
                        .toMap()
                    val error = headers.entries
                        .firstOrNull { it.key.equals("X-Lens-Error", ignoreCase = true) }?.value
                    _uiState.value = _uiState.value.copy(
                        timings = stages,
                        errorMessage = error?.let { "The backend hit a problem ($it)." },
                    )
                }
            }
            val source = ProgressiveMediaSource.Factory(factory)
                .createMediaSource(MediaItem.fromUri("lens://ask"))
            player.setMediaSource(source)
            player.prepare()
            player.play()
        }
    }

    override fun onCleared() {
        player.release()
    }
}
