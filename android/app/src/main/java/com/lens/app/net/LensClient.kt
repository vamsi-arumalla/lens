package com.lens.app.net

import com.lens.app.data.LensSettings
import java.io.File
import java.util.concurrent.TimeUnit
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody

object LensClient {

    val http: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        // The answer streams for as long as the model talks; no read timeout cliff
        .readTimeout(60, TimeUnit.SECONDS)
        .build()

    fun askRequest(
        settings: LensSettings,
        frames: List<ByteArray>,
        audio: File?,
        text: String? = null,
    ): Request {
        require(frames.size in 1..3) { "contract allows 1..3 frames" }
        val body = MultipartBody.Builder().setType(MultipartBody.FORM).apply {
            frames.forEachIndexed { i, jpeg ->
                addFormDataPart(
                    "frames", "frame-$i.jpg",
                    jpeg.toRequestBody("image/jpeg".toMediaType()),
                )
            }
            if (audio != null) {
                addFormDataPart(
                    "audio", audio.name,
                    audio.asRequestBody("audio/mp4".toMediaType()),
                )
            }
            if (!text.isNullOrBlank()) {
                addFormDataPart("text", text)
            }
        }.build()

        return Request.Builder()
            .url("${settings.backendUrl.trimEnd('/')}/ask")
            .header("X-API-Key", settings.apiKey)
            .post(body)
            .build()
    }
}
