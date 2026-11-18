package com.example.mybroker_admin.notification

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.example.mybroker_admin.MainActivity
import com.example.mybroker_admin.R

object NotificationHelper {
    private const val CHANNEL_ID = "mybroker_general"
    private const val CHANNEL_NAME = "MyBroker Notifications"

    fun ensureChannel(context: Context) {
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (manager.getNotificationChannel(CHANNEL_ID) != null) return

        val channel = NotificationChannel(
            CHANNEL_ID,
            CHANNEL_NAME,
            NotificationManager.IMPORTANCE_HIGH
        )
        manager.createNotificationChannel(channel)
    }

    fun showNotification(
        context: Context,
        title: String,
        body: String,
        data: NotificationData
    ) {
        ensureChannel(context)

        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra(NotificationData.EXTRA_TYPE, data.type)
            putExtra(NotificationData.EXTRA_PROPERTY_ID, data.propertyId)
            putExtra(NotificationData.EXTRA_NOTIFICATION_ID, data.notificationId)
            putExtra(NotificationData.EXTRA_ROLE_TARGET, data.roleTarget)
        }

        val requestCode = (
            (data.type ?: "") + ":" +
                (data.propertyId ?: "") + ":" +
                (data.notificationId ?: "")
            ).hashCode()

        val pendingIntent = PendingIntent.getActivity(
            context,
            requestCode,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle(title)
            .setContentText(body)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .build()

        NotificationManagerCompat.from(context).notify(System.currentTimeMillis().toInt(), notification)
    }
}
