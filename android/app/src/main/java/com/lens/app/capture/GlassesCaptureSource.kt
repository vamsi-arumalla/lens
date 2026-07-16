package com.lens.app.capture

import com.lens.app.glasses.GlassesManager

/**
 * Phase 3 capture device: Meta glasses via the DAT SDK. Produces the same
 * JPEG frames as the phone source — the /ask contract does not change.
 */
class GlassesCaptureSource(private val manager: GlassesManager) : CaptureSource {
    override suspend fun captureFrames(): List<ByteArray> =
        listOf(manager.capturePhotoJpeg())
}
