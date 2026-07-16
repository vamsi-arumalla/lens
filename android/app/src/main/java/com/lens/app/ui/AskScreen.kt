package com.lens.app.ui

import android.Manifest
import android.content.pm.PackageManager
import android.util.Size
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.Preview
import androidx.camera.core.resolutionselector.ResolutionSelector
import androidx.camera.core.resolutionselector.ResolutionStrategy
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BugReport
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.lens.app.AskStatus
import com.lens.app.AskViewModel
import com.lens.app.audio.VoiceRecorder
import com.lens.app.capture.CaptureSource
import com.lens.app.capture.GlassesCaptureSource
import com.lens.app.capture.PhoneCaptureSource
import com.lens.app.glasses.GlassesRuntime
import com.lens.app.glasses.GlassesState
import kotlinx.coroutines.async
import kotlinx.coroutines.withTimeout

private val REQUIRED_PERMISSIONS =
    arrayOf(Manifest.permission.CAMERA, Manifest.permission.RECORD_AUDIO)

@Composable
fun AskScreen(viewModel: AskViewModel, onOpenSettings: () -> Unit) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val uiState by viewModel.uiState.collectAsState()

    var permissionsGranted by remember {
        mutableStateOf(
            REQUIRED_PERMISSIONS.all {
                ContextCompat.checkSelfPermission(context, it) == PackageManager.PERMISSION_GRANTED
            }
        )
    }
    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { result -> permissionsGranted = result.values.all { it } }

    LaunchedEffect(Unit) {
        if (!permissionsGranted) permissionLauncher.launch(REQUIRED_PERMISSIONS)
    }

    if (!permissionsGranted) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text("Lens needs camera and microphone access.")
        }
        return
    }

    val recorder = remember { VoiceRecorder(context) }
    val imageCapture = remember {
        // The backend downscales to 1280px anyway; capturing near that size
        // saves several MB of upload per ask
        ImageCapture.Builder()
            .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
            .setResolutionSelector(
                ResolutionSelector.Builder()
                    .setResolutionStrategy(
                        ResolutionStrategy(
                            Size(1280, 960),
                            ResolutionStrategy.FALLBACK_RULE_CLOSEST_HIGHER_THEN_LOWER,
                        )
                    )
                    .build()
            )
            .setJpegQuality(85)
            .build()
    }
    // The capture device behind the ask flow: glasses when a stream is live,
    // phone otherwise. Everything downstream (request shape, playback) is
    // shared, and a dropped glasses stream falls back to phone automatically.
    val captureScope = rememberCoroutineScope()
    val glassesState by GlassesRuntime.manager.state.collectAsState()
    val phoneSource: CaptureSource = remember(imageCapture) {
        PhoneCaptureSource(imageCapture, ContextCompat.getMainExecutor(context))
    }
    val captureSource: CaptureSource =
        if (glassesState == GlassesState.READY) {
            remember { GlassesCaptureSource(GlassesRuntime.manager) }
        } else {
            phoneSource
        }

    Box(Modifier.fillMaxSize()) {
        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = { ctx ->
                val previewView = PreviewView(ctx)
                val providerFuture = ProcessCameraProvider.getInstance(ctx)
                providerFuture.addListener({
                    val provider = providerFuture.get()
                    val preview = Preview.Builder().build().also {
                        it.surfaceProvider = previewView.surfaceProvider
                    }
                    provider.unbindAll()
                    provider.bindToLifecycle(
                        lifecycleOwner,
                        CameraSelector.DEFAULT_BACK_CAMERA,
                        preview,
                        imageCapture,
                    )
                }, ContextCompat.getMainExecutor(ctx))
                previewView
            },
        )

        IconButton(onClick = onOpenSettings, modifier = Modifier.align(Alignment.TopEnd).padding(8.dp)) {
            Icon(Icons.Filled.Settings, "Settings", tint = Color.White)
        }
        IconButton(
            onClick = viewModel::toggleDebugOverlay,
            modifier = Modifier.align(Alignment.TopStart).padding(8.dp),
        ) {
            Icon(Icons.Filled.BugReport, "Toggle timings", tint = Color.White)
        }

        if (uiState.showDebugOverlay && uiState.timings.isNotEmpty()) {
            Surface(
                modifier = Modifier.align(Alignment.TopCenter).padding(top = 12.dp),
                color = Color.Black.copy(alpha = 0.6f),
                shape = MaterialTheme.shapes.small,
            ) {
                Column(Modifier.padding(8.dp)) {
                    uiState.timings.forEach { (stage, ms) ->
                        Text("$stage: ${ms}ms", color = Color.White, style = MaterialTheme.typography.labelSmall)
                    }
                }
            }
        }

        Column(
            modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = 32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            if (glassesState == GlassesState.READY) {
                Text(
                    "GLASSES",
                    color = Color.White,
                    style = MaterialTheme.typography.labelSmall,
                    modifier = Modifier
                        .padding(bottom = 6.dp)
                        .background(Color(0xFF6650A4), MaterialTheme.shapes.small)
                        .padding(horizontal = 10.dp, vertical = 3.dp),
                )
            }
            val statusText = when (uiState.status) {
                AskStatus.IDLE -> "Hold to ask"
                AskStatus.RECORDING -> "Listening…"
                AskStatus.THINKING -> "Thinking…"
                AskStatus.SPEAKING -> "Speaking"
                AskStatus.ERROR -> uiState.errorMessage ?: "Something went wrong."
            }
            Text(
                statusText,
                color = Color.White,
                modifier = Modifier
                    .background(Color.Black.copy(alpha = 0.5f), MaterialTheme.shapes.small)
                    .padding(horizontal = 12.dp, vertical = 6.dp),
            )

            Box(
                modifier = Modifier
                    .padding(top = 16.dp)
                    .size(88.dp)
                    .background(
                        if (uiState.status == AskStatus.RECORDING) Color.Red else Color.White,
                        CircleShape,
                    )
                    .pointerInput(Unit) {
                        detectTapGestures(
                            onPress = {
                                // Press: freeze the frame(s) + start listening.
                                // runCatching keeps a capture failure from
                                // cancelling the whole scope; a dead glasses
                                // capture falls back to the phone in-press.
                                val framesJob = captureScope.async {
                                    runCatching { captureSource.captureFrames() }
                                        .recoverCatching { e ->
                                            if (captureSource !== phoneSource) {
                                                phoneSource.captureFrames()
                                            } else {
                                                throw e
                                            }
                                        }
                                }
                                try {
                                    recorder.start()
                                    viewModel.onRecordingStarted()
                                } catch (e: Exception) {
                                    viewModel.cancelToIdle()
                                }
                                tryAwaitRelease()
                                // Release: stop listening, ship the question.
                                // The timeout keeps a stuck capture from
                                // deadlocking the gesture handler for good.
                                val audio = recorder.stop()
                                try {
                                    val frames = withTimeout(4000) { framesJob.await() }
                                    viewModel.ask(frames.getOrThrow(), audio)
                                } catch (e: Exception) {
                                    viewModel.showError("Camera capture failed — try again.")
                                }
                            }
                        )
                    },
            )
        }
    }
}
