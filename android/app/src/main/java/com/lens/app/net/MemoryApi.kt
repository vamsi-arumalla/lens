package com.lens.app.net

import com.lens.app.data.LensSettings
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
                createdAt = m.getString("created_at").take(16).replace("T", " "),
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
