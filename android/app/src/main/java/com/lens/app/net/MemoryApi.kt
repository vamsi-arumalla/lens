package com.lens.app.net

import com.lens.app.data.LensSettings
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject

data class Moment(
    val id: String,
    val createdAt: String,
    val caption: String,
    val transcript: String,
    val question: String,
    val answer: String,
    val thumbUrl: String,
    val frameUrl: String,
)

private val LOCAL_TIME = DateTimeFormatter.ofPattern("MMM d, HH:mm")

private fun toLocalTime(isoUtc: String): String = try {
    OffsetDateTime.parse(isoUtc)
        .atZoneSameInstant(ZoneId.systemDefault())
        .format(LOCAL_TIME)
} catch (e: Exception) {
    isoUtc.take(16).replace("T", " ")
}

class MemoryApi(private val settings: LensSettings) {

    private val base = settings.backendUrl.trimEnd('/')

    private fun builder(path: String) =
        Request.Builder().url(base + path).header("X-API-Key", settings.apiKey)

    private fun parseMoments(json: String): List<Moment> {
        val array: JSONArray = JSONObject(json).getJSONArray("moments")
        return (0 until array.length()).map { i ->
            val m = array.getJSONObject(i)
            Moment(
                id = m.getString("id"),
                createdAt = toLocalTime(m.getString("created_at")),
                caption = m.optString("caption"),
                transcript = m.optString("transcript"),
                question = m.optString("question"),
                answer = m.optString("answer"),
                thumbUrl = base + m.getString("thumb_url"),
                frameUrl = base + m.getString("frame_url"),
            )
        }
    }

    private fun run(request: Request): String =
        LensClient.http.newCall(request).execute().use { resp ->
            if (!resp.isSuccessful) throw java.io.IOException("HTTP ${resp.code}")
            resp.body?.string().orEmpty()
        }

    suspend fun recent(): List<Moment> = withContext(Dispatchers.IO) {
        parseMoments(run(builder("/memory/recent").get().build()))
    }

    suspend fun search(query: String): List<Moment> = withContext(Dispatchers.IO) {
        val body = JSONObject().put("query", query).put("limit", 30).toString()
            .toRequestBody("application/json".toMediaType())
        parseMoments(run(builder("/memory/search").post(body).build()))
    }

    suspend fun delete(id: String): Unit = withContext(Dispatchers.IO) {
        run(builder("/memory/$id").delete().build())
    }
}
