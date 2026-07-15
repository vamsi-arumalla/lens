package com.lens.app

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.lens.app.data.LensSettings
import com.lens.app.data.SettingsStore
import com.lens.app.net.MemoryApi
import com.lens.app.net.Moment
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class MemoriesUiState(
    val moments: List<Moment> = emptyList(),
    val loading: Boolean = false,
    val error: String? = null,
    val selected: Moment? = null,
)

class MemoriesViewModel(app: Application) : AndroidViewModel(app) {

    private val settingsStore = SettingsStore(app)

    val settings: StateFlow<LensSettings> = settingsStore.settings
        .stateIn(viewModelScope, SharingStarted.Eagerly, LensSettings())

    private val _uiState = MutableStateFlow(MemoriesUiState())
    val uiState: StateFlow<MemoriesUiState> = _uiState

    private suspend fun api() = MemoryApi(settingsStore.current())

    fun refresh(query: String = "") {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null)
            try {
                val moments =
                    if (query.isBlank()) api().recent() else api().search(query)
                _uiState.value = _uiState.value.copy(moments = moments, loading = false)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    error = "Couldn't load memories — is the backend up?",
                )
            }
        }
    }

    fun select(moment: Moment?) {
        _uiState.value = _uiState.value.copy(selected = moment)
    }

    fun delete(moment: Moment) {
        viewModelScope.launch {
            try {
                api().delete(moment.id)
                _uiState.value = _uiState.value.copy(
                    moments = _uiState.value.moments.filterNot { it.id == moment.id },
                    selected = null,
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = "Delete failed.")
            }
        }
    }
}
