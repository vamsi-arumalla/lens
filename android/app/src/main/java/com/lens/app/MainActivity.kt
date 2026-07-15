package com.lens.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import com.lens.app.ui.AskScreen
import com.lens.app.ui.MemoriesScreen
import com.lens.app.ui.SettingsScreen

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface {
                    val askVm: AskViewModel = viewModel()
                    val memoriesVm: MemoriesViewModel = viewModel()
                    var showSettings by remember { mutableStateOf(false) }
                    var tab by remember { mutableIntStateOf(0) }

                    if (showSettings) {
                        SettingsScreen(askVm, onDone = { showSettings = false })
                        return@Surface
                    }
                    Scaffold(
                        bottomBar = {
                            NavigationBar {
                                NavigationBarItem(
                                    selected = tab == 0,
                                    onClick = { tab = 0 },
                                    icon = { Icon(Icons.Filled.CameraAlt, null) },
                                    label = { Text("Ask") },
                                )
                                NavigationBarItem(
                                    selected = tab == 1,
                                    onClick = { tab = 1 },
                                    icon = { Icon(Icons.Filled.PhotoLibrary, null) },
                                    label = { Text("Memories") },
                                )
                            }
                        }
                    ) { padding ->
                        Box(Modifier.fillMaxSize().padding(padding)) {
                            when (tab) {
                                0 -> AskScreen(askVm, onOpenSettings = { showSettings = true })
                                else -> MemoriesScreen(memoriesVm)
                            }
                        }
                    }
                }
            }
        }
    }
}
