package com.example.smartagriculture.util

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import androidx.core.app.NotificationCompat

object NotificationHelper {
    private const val CHANNEL_ID = "smart_agriculture_alerts"
    private const val CHANNEL_NAME = "Cảnh Báo Nông Nghiệp"
    private var lastAlertTime = 0L
    private const val COOLDOWN_MS = 10 * 60 * 1000L // Chống spam thông báo (10 phút 1 lần)

    fun sendAlertNotification(context: Context, title: String, message: String) {
        val currentTime = System.currentTimeMillis()
        if (currentTime - lastAlertTime < COOLDOWN_MS) {
            return
        }
        lastAlertTime = currentTime

        val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        // Tạo NotificationChannel cho Android 8.0 (API 26) trở lên
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Kênh gửi thông báo khẩn cấp khi cây thiếu nước hoặc nhiệt độ quá cao"
            }
            notificationManager.createNotificationChannel(channel)
        }

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.stat_notify_error)
            .setContentTitle(title)
            .setContentText(message)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .build()

        notificationManager.notify(1001, notification)
    }
}

