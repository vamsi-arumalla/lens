package com.lens.app.net

import android.net.Uri
import androidx.media3.common.C
import androidx.media3.common.util.UnstableApi
import androidx.media3.datasource.BaseDataSource
import androidx.media3.datasource.DataSpec
import java.io.IOException
import java.io.InputStream
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response

/**
 * Media3 DataSource that POSTs the /ask multipart request and exposes the
 * chunked audio response as the playback stream, so the answer starts playing
 * while the backend is still generating it.
 */
@UnstableApi
class StreamingDataSource(
    private val client: OkHttpClient,
    private val request: Request,
    private val onHeaders: (Map<String, String>) -> Unit,
) : BaseDataSource(/* isNetwork = */ true) {

    private var response: Response? = null
    private var input: InputStream? = null
    private var uri: Uri? = null

    override fun open(dataSpec: DataSpec): Long {
        uri = dataSpec.uri
        transferInitializing(dataSpec)
        val resp = client.newCall(request).execute()
        if (!resp.isSuccessful) {
            val code = resp.code
            resp.close()
            throw IOException("backend returned HTTP $code")
        }
        response = resp
        onHeaders(resp.headers.names().associateWith { resp.headers[it].orEmpty() })
        input = resp.body?.byteStream() ?: throw IOException("empty response body")
        transferStarted(dataSpec)
        return C.LENGTH_UNSET.toLong()
    }

    override fun read(buffer: ByteArray, offset: Int, length: Int): Int {
        if (length == 0) return 0
        val n = input?.read(buffer, offset, length) ?: return C.RESULT_END_OF_INPUT
        if (n == -1) return C.RESULT_END_OF_INPUT
        bytesTransferred(n)
        return n
    }

    override fun getUri(): Uri? = uri

    override fun close() {
        try {
            input?.close()
            response?.close()
        } finally {
            input = null
            response = null
            transferEnded()
        }
    }
}
