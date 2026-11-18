package com.example.myapplication.notification

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import com.example.myapplication.R

object NotificationChannels {
    const val USER_NOTIFICATIONS = "user_notifications"

    fun create(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return

        val manager = context.getSystemService(NotificationManager::class.java) ?: return
        if (manager.getNotificationChannel(USER_NOTIFICATIONS) != null) return

        manager.createNotificationChannel(
            NotificationChannel(
                USER_NOTIFICATIONS,
                context.getString(R.string.app_name),
                NotificationManager.IMPORTANCE_DEFAULT
            )
        )
    }
}
