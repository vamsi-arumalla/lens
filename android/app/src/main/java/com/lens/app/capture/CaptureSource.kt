package com.lens.app.capture

/**
 * A device that can produce "what the user is looking at right now".
 *
 * Every capture path — phone camera today, Meta glasses in Phase 3 — funnels
 * through this interface into the same request builder (LensClient), so the
 * /ask wire contract (docs/ask-contract.md) is identical by construction no
 * matter which device produced the frames.
 */
interface CaptureSource {
    /** Grab 1..3 JPEG-encoded frames. Invoked when the user starts asking. */
    suspend fun captureFrames(): List<ByteArray>
}
