package com.lens.app

import com.lens.app.capture.CaptureSource
import com.lens.app.data.LensSettings
import com.lens.app.net.LensClient
import java.io.File
import kotlinx.coroutines.runBlocking
import okio.Buffer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Asserts that any CaptureSource funnelled through LensClient produces an
 * /ask request matching docs/ask-contract.md — the canonical ingestion
 * contract. The glasses capture path (Phase 3) must pass this unchanged.
 */
class AskContractTest {

    /** Stands in for the DAT glasses adapter: JPEG frames, possibly a burst. */
    private class FakeGlassesCaptureSource(private val burst: Int) : CaptureSource {
        override suspend fun captureFrames(): List<ByteArray> =
            List(burst) { JPEG_MAGIC + byteArrayOf(it.toByte()) }
    }

    private val settings =
        LensSettings(backendUrl = "http://10.0.0.7:8400/", apiKey = "secret-key")

    private fun serializedParts(request: okhttp3.Request): List<String> {
        val boundary = (request.body!!.contentType()!!).parameter("boundary")!!
        val buffer = Buffer().also { request.body!!.writeTo(it) }
        val raw = buffer.readByteString().utf8()
        return raw.split("--$boundary").filter { it.contains("Content-Disposition") }
    }

    @Test
    fun `glasses capture path produces a contract-conforming ask request`() = runBlocking {
        val frames = FakeGlassesCaptureSource(burst = 2).captureFrames()
        val audio = File.createTempFile("question", ".m4a").apply { writeBytes(ByteArray(64)) }
        val request = LensClient.askRequest(settings, frames, audio)

        // Method, path, auth — exact per contract
        assertEquals("POST", request.method)
        assertEquals("/ask", request.url.encodedPath)
        assertEquals("secret-key", request.header("X-API-Key"))
        assertEquals("multipart", request.body!!.contentType()!!.type)
        assertEquals("form-data", request.body!!.contentType()!!.subtype)

        val parts = serializedParts(request)

        val frameParts = parts.filter { it.contains("name=\"frames\"") }
        assertEquals(2, frameParts.size)
        frameParts.forEach { part ->
            assertTrue("frames part must carry a filename", part.contains("filename="))
            assertTrue("frames part must be image/jpeg", part.contains("Content-Type: image/jpeg"))
        }

        val audioParts = parts.filter { it.contains("name=\"audio\"") }
        assertEquals(1, audioParts.size)
        assertTrue(audioParts[0].contains("filename="))
        assertTrue("audio part must be audio/mp4", audioParts[0].contains("Content-Type: audio/mp4"))

        // No text part was supplied; no stray fields allowed
        assertEquals(3, parts.size)
    }

    @Test
    fun `text part is a plain field with no filename or content type`() = runBlocking {
        val frames = FakeGlassesCaptureSource(burst = 1).captureFrames()
        val request = LensClient.askRequest(settings, frames, audio = null, text = "what is this?")
        val parts = serializedParts(request)

        val textPart = parts.single { it.contains("name=\"text\"") }
        assertFalse("text part must not have a filename", textPart.contains("filename="))
        assertFalse("text part must not have a content type", textPart.contains("Content-Type"))
        assertTrue(textPart.contains("what is this?"))
    }

    @Test
    fun `contract rejects more than three frames client-side`() {
        val frames = List(4) { JPEG_MAGIC }
        try {
            LensClient.askRequest(settings, frames, audio = null, text = "q")
            throw AssertionError("expected IllegalArgumentException for 4 frames")
        } catch (expected: IllegalArgumentException) {
        }
    }

    private companion object {
        val JPEG_MAGIC = byteArrayOf(0xFF.toByte(), 0xD8.toByte(), 0xFF.toByte())
    }
}
