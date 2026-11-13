package com.example.smartagriculture.data.remote

import android.util.Log
import com.example.smartagriculture.data.model.LatestStatusResponse
import com.google.gson.Gson
import okhttp3.*
import java.util.concurrent.TimeUnit

class FarmWebSocketManager(
    private val serverWsUrl: String = "ws://172.20.10.2:8000/ws/live-data",
    private val onDataReceived: (LatestStatusResponse) -> Unit,
    private val onConnectionStatusChanged: (Boolean) -> Unit
) {
    private val client: OkHttpClient = OkHttpClient.Builder()
        .readTimeout(10, TimeUnit.SECONDS)
        .retryOnConnectionFailure(true)
        .build()

    private var webSocket: WebSocket? = null
    private val gson = Gson()
    private var isManuallyClosed = false

    fun connect() {
        isManuallyClosed = false
        val request = Request.Builder().url(serverWsUrl).build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.d("FarmWebSocket", "✅ WebSocket kết nối thành công tới $serverWsUrl")
                onConnectionStatusChanged(true)
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                try {
                    // Phân tích cú pháp dữ liệu thời gian thực được đẩy trực tiếp từ server
                    val data = gson.fromJson(text, LatestStatusResponse::class.java)
                    if (data != null && data.airTemp != null) {
                        onDataReceived(data)
                    }
                } catch (e: Exception) {
                    Log.e("FarmWebSocket", "Lỗi giải mã JSON WebSocket: ${e.message}")
                }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.w("FarmWebSocket", "⚠️ WebSocket mất kết nối: ${t.message}. Đang thử kết nối lại...")
                onConnectionStatusChanged(false)
                reconnect()
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                Log.d("FarmWebSocket", "WebSocket đã đóng: $reason")
                onConnectionStatusChanged(false)
                if (!isManuallyClosed) {
                    reconnect()
                }
            }
        })
    }

    private fun reconnect() {
        if (isManuallyClosed) return
        Thread {
            try {
                Thread.sleep(3000)
                connect()
            } catch (_: Exception) {}
        }.start()
    }

    fun close() {
        isManuallyClosed = true
        webSocket?.close(1000, "App closed")
    }
}
