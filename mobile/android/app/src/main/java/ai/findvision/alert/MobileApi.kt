package ai.findvision.alert

import android.content.Context
import org.json.JSONObject
import java.io.File
import java.net.CookieHandler
import java.net.CookieManager
import java.net.CookiePolicy
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

class MobileApi(private val context: Context, private val baseUrl: String, private val accessKey: String) {
    init {
        if (CookieHandler.getDefault() == null) {
            CookieHandler.setDefault(CookieManager(null, CookiePolicy.ACCEPT_ALL))
        }
    }

    fun generateReference(originalText: String): File {
        request("GET", "/api/session")
        val analyzed = JSONObject(request("POST", "/api/analyze", JSONObject().put("text", originalText)))
        val features = analyzed.getJSONObject("features")
        val jobResponse = JSONObject(request("POST", "/api/generate", JSONObject()
            .put("features", features).put("mode", "fast")))
        val id = jobResponse.getString("id")
        val expiresAt = System.currentTimeMillis() + 4 * 60 * 1000
        while (System.currentTimeMillis() < expiresAt) {
            Thread.sleep(1200)
            val status = JSONObject(request("GET", "/api/jobs/$id"))
            when (status.optString("state")) {
                "done" -> {
                    val bytes = requestBytes("GET", "/api/jobs/$id/image")
                    val dir = File(context.filesDir, "alert-images").apply { mkdirs() }
                    prune(dir)
                    val name = sha256(originalText + System.currentTimeMillis()) + ".img"
                    return File(dir, name).apply { writeBytes(bytes) }
                }
                "error" -> throw IllegalStateException(status.optString("error", "이미지를 만들지 못했습니다."))
            }
        }
        throw IllegalStateException("이미지 생성 응답을 기다리는 시간이 초과되었습니다.")
    }

    private fun request(method: String, path: String, json: JSONObject? = null): String {
        val connection = open(method, path, json != null)
        try {
            if (json != null) connection.outputStream.use { it.write(json.toString().toByteArray(Charsets.UTF_8)) }
            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val response = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            if (code !in 200..299) {
                val detail = runCatching { JSONObject(response).optString("detail") }.getOrNull()
                throw IllegalStateException(detail?.takeIf(String::isNotBlank) ?: "서버 요청에 실패했습니다 ($code).")
            }
            return response
        } finally { connection.disconnect() }
    }

    private fun requestBytes(method: String, path: String): ByteArray {
        val connection = open(method, path, false)
        try {
            val code = connection.responseCode
            if (code !in 200..299) throw IllegalStateException("생성 이미지를 받지 못했습니다 ($code).")
            return connection.inputStream.use { it.readBytes() }
        } finally { connection.disconnect() }
    }

    private fun open(method: String, path: String, body: Boolean): HttpURLConnection {
        val connection = URL(baseUrl.trimEnd('/') + path).openConnection() as HttpURLConnection
        connection.requestMethod = method
        connection.connectTimeout = 15000
        connection.readTimeout = 120000
        connection.setRequestProperty("Origin", baseUrl.trimEnd('/'))
        connection.setRequestProperty("Authorization", "Bearer $accessKey")
        connection.setRequestProperty("X-FindVision", "1")
        connection.setRequestProperty("Accept", "application/json")
        connection.instanceFollowRedirects = false
        if (body) {
            connection.doOutput = true
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
        }
        return connection
    }

    private fun prune(dir: File) {
        dir.listFiles()?.sortedByDescending(File::lastModified)?.drop(24)?.forEach(File::delete)
    }

    private fun sha256(value: String): String = MessageDigest.getInstance("SHA-256")
        .digest(value.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }.take(24)
}
