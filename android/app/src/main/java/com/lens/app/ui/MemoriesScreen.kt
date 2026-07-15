package com.lens.app.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
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
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import coil.ImageLoader
import coil.compose.AsyncImage
import com.lens.app.MemoriesViewModel
import com.lens.app.net.LensClient

@Composable
fun MemoriesScreen(viewModel: MemoriesViewModel) {
    val context = LocalContext.current
    val uiState by viewModel.uiState.collectAsState()
    val settings by viewModel.settings.collectAsState()
    var query by remember { mutableStateOf("") }

    // Thumbnails live behind the API key, so Coil needs a client that sends it
    val imageLoader = remember(settings.apiKey) {
        ImageLoader.Builder(context)
            .okHttpClient(
                LensClient.http.newBuilder()
                    .addInterceptor { chain ->
                        chain.proceed(
                            chain.request().newBuilder()
                                .header("X-API-Key", settings.apiKey)
                                .build()
                        )
                    }
                    .build()
            )
            .build()
    }

    LaunchedEffect(Unit) { viewModel.refresh() }

    Column(Modifier.fillMaxSize().padding(12.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(
                value = query,
                onValueChange = { query = it },
                label = { Text("Search memories") },
                singleLine = true,
                modifier = Modifier.weight(1f),
            )
            IconButton(onClick = { viewModel.refresh(query) }) {
                Icon(Icons.Filled.Search, "Search")
            }
            if (query.isNotBlank()) {
                IconButton(onClick = { query = ""; viewModel.refresh() }) {
                    Icon(Icons.Filled.Close, "Clear")
                }
            }
        }

        when {
            uiState.loading -> CircularProgressIndicator(
                Modifier.align(Alignment.CenterHorizontally).padding(32.dp)
            )
            uiState.error != null -> Text(
                uiState.error!!,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.padding(16.dp),
            )
            uiState.moments.isEmpty() -> Text(
                "No memories yet — everything you ask about gets remembered here.",
                modifier = Modifier.padding(16.dp),
            )
            else -> LazyVerticalGrid(
                columns = GridCells.Adaptive(minSize = 108.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                modifier = Modifier.padding(top = 10.dp),
            ) {
                items(uiState.moments, key = { it.id }) { moment ->
                    AsyncImage(
                        model = moment.thumbUrl,
                        imageLoader = imageLoader,
                        contentDescription = moment.caption,
                        modifier = Modifier
                            .fillMaxWidth()
                            .aspectRatio(1f)
                            .clickable { viewModel.select(moment) },
                    )
                }
            }
        }
    }

    uiState.selected?.let { moment ->
        AlertDialog(
            onDismissRequest = { viewModel.select(null) },
            confirmButton = {
                TextButton(onClick = { viewModel.delete(moment) }) {
                    Icon(Icons.Filled.Delete, null)
                    Text("Delete")
                }
            },
            dismissButton = {
                TextButton(onClick = { viewModel.select(null) }) { Text("Close") }
            },
            title = { Text(moment.createdAt) },
            text = {
                Column {
                    AsyncImage(
                        model = moment.frameUrl,
                        imageLoader = imageLoader,
                        contentDescription = moment.caption,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Text(moment.caption, Modifier.padding(top = 8.dp))
                    if (moment.transcript.isNotBlank()) {
                        Text("Heard: ${moment.transcript}", Modifier.padding(top = 4.dp))
                    }
                    if (moment.question.isNotBlank()) {
                        Text(
                            "Q: ${moment.question}\nA: ${moment.answer}",
                            Modifier.padding(top = 4.dp),
                        )
                    }
                }
            },
        )
    }
}
