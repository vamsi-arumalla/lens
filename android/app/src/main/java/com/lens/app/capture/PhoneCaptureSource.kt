package com.lens.app.capture

import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.ImageProxy
import java.util.concurrent.Executor
import kotlinx.coroutines.CompletableDeferred

/** Phase 1 capture device: the phone's CameraX ImageCapture use case. */
class PhoneCaptureSource(
    private val imageCapture: ImageCapture,
    private val executor: Executor,
) : CaptureSource {

    override suspend fun captureFrames(): List<ByteArray> {
        val deferred = CompletableDeferred<ByteArray>()
        imageCapture.takePicture(
            executor,
            object : ImageCapture.OnImageCapturedCallback() {
                override fun onCaptureSuccess(image: ImageProxy) {
                    image.use { deferred.complete(it.jpegBytes()) }
                }

                override fun onError(exception: ImageCaptureException) {
                    deferred.completeExceptionally(exception)
                }
            },
        )
        return listOf(deferred.await())
    }

    private fun ImageProxy.jpegBytes(): ByteArray {
        val buffer = planes[0].buffer
        return ByteArray(buffer.remaining()).also { buffer.get(it) }
    }
}
