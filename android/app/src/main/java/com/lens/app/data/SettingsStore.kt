package com.lens.app.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "lens_settings")

data class LensSettings(
    val backendUrl: String = "http://192.168.1.10:8000",
    val apiKey: String = "dev-key",
)

class SettingsStore(private val context: Context) {

    private val urlKey = stringPreferencesKey("backend_url")
    private val apiKeyKey = stringPreferencesKey("api_key")

    val settings: Flow<LensSettings> = context.dataStore.data.map { prefs ->
        LensSettings(
            backendUrl = prefs[urlKey] ?: LensSettings().backendUrl,
            apiKey = prefs[apiKeyKey] ?: LensSettings().apiKey,
        )
    }

    suspend fun current(): LensSettings = settings.first()

    suspend fun save(newSettings: LensSettings) {
        context.dataStore.edit { prefs ->
            prefs[urlKey] = newSettings.backendUrl.trimEnd('/')
            prefs[apiKeyKey] = newSettings.apiKey
        }
    }
}
