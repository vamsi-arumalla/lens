package com.lens.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.Switch
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.lens.app.AskViewModel
import com.lens.app.BuildConfig
import com.lens.app.data.LensSettings
import com.lens.app.glasses.GlassesRuntime
import com.lens.app.glasses.GlassesState
import com.lens.app.glasses.MockGlassesController
import kotlinx.coroutines.launch

@Composable
fun SettingsScreen(viewModel: AskViewModel, onDone: () -> Unit) {
    val saved by viewModel.settings.collectAsState()
    var url by remember { mutableStateOf(saved.backendUrl) }
    var apiKey by remember { mutableStateOf(saved.apiKey) }
    LaunchedEffect(saved) {
        url = saved.backendUrl
        apiKey = saved.apiKey
    }
    val scope = rememberCoroutineScope()

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text("Settings", style = MaterialTheme.typography.headlineSmall)
        OutlinedTextField(
            value = url,
            onValueChange = { url = it },
            label = { Text("Backend URL (e.g. http://192.168.1.10:8000)") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = apiKey,
            onValueChange = { apiKey = it },
            label = { Text("API key") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Button(onClick = {
            scope.launch {
                viewModel.settingsStore.save(LensSettings(backendUrl = url, apiKey = apiKey))
                onDone()
            }
        }) { Text("Save") }
        TextButton(onClick = onDone) { Text("Cancel") }

        if (BuildConfig.DEBUG) {
            val context = LocalContext.current
            val glassesState by GlassesRuntime.manager.state.collectAsState()
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Mock glasses (debug)")
                    Text(
                        "MockDeviceKit Ray-Ban Meta fed by the phone camera — $glassesState",
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                Switch(
                    checked = glassesState == GlassesState.READY ||
                        glassesState == GlassesState.CONNECTING,
                    onCheckedChange = { on ->
                        if (on) {
                            MockGlassesController.start(context)
                            GlassesRuntime.scope.launch { GlassesRuntime.manager.connect() }
                        } else {
                            MockGlassesController.stop(context)
                        }
                    },
                )
            }
            Row {
                TextButton(onClick = { MockGlassesController.fold(context) }) {
                    Text("Fold")
                }
                TextButton(onClick = { MockGlassesController.unfold(context) }) {
                    Text("Unfold")
                }
                TextButton(onClick = {
                    GlassesRuntime.scope.launch { GlassesRuntime.manager.connect() }
                }) {
                    Text("Reconnect")
                }
            }
        }
    }
}
