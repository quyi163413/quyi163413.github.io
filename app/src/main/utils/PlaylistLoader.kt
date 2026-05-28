package com.iptv.player.utils

import com.iptv.player.model.Channel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.BufferedReader
import java.io.StringReader
import java.util.concurrent.TimeUnit

object PlaylistLoader {
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .build()

    suspend fun loadFromUrl(url: String): Result<List<Channel>> = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder().url(url).build()
            val response = client.newCall(request).execute()
            if (!response.isSuccessful) {
                return@withContext Result.failure(Exception("HTTP ${response.code}"))
            }
            val body = response.body?.string() ?: ""
            val channels = parseTxt(body)
            if (channels.isEmpty()) {
                Result.failure(Exception("No channels found"))
            } else {
                Result.success(channels)
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    private fun parseTxt(content: String): List<Channel> {
        val channels = mutableListOf<Channel>()
        BufferedReader(StringReader(content)).use { reader ->
            var line: String?
            while (reader.readLine().also { line = it } != null) {
                val l = line?.trim() ?: continue
                if (l.isBlank() || l.startsWith("#")) continue
                val parts = l.split(",", limit = 2)
                if (parts.size == 2) {
                    val name = parts[0].trim()
                    val url = parts[1].trim()
                    if (url.startsWith("http")) {
                        channels.add(Channel(name, url))
                    }
                } else if (l.startsWith("http")) {
                    // 如果没有名字，使用URL作为名字
                    channels.add(Channel("频道${channels.size+1}", l))
                }
            }
        }
        return channels
    }
}
