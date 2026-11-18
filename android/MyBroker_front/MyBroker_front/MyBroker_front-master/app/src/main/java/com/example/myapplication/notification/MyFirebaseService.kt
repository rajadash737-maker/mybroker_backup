package com.example.myapplication.notification

import android.Manifest
import android.app.PendingIntent
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.example.myapplication.MainActivity
import com.example.myapplication.R
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

class MyFirebaseService : FirebaseMessagingService() {
    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        FcmTokenManager.onNewToken(applicationContext, token)
    }

    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)

        val data = message.data
        val title = message.notification?.title
            ?: data["title"]
            ?: getString(R.string.app_name)
        val body = message.notification?.body ?: data["body"] ?: return
        val type = data["type"] ?: data["notification_type"]
        val referenceId = data["reference_id"] ?: data["referenceId"]
            ?: data["property_id"] ?: data["propertyId"]
        val roleTarget = data["role_target"] ?: data["roleTarget"]
        val notificationId = data["notification_id"]?.toIntOrNull()
            ?: data["id"]?.toIntOrNull()
        val timestamp = System.currentTimeMillis()

        NotificationStore.add(
            applicationContext,
            NotificationItem(
                id = notificationId,
                title = title,
                body = body,
                type = type,
                referenceId = referenceId,
                roleTarget = roleTarget,
                timestamp = timestamp
            )
        )

        serviceScope.launch {
            val enabled = runCatching {
                NotificationPreferences.notificationsEnabledFlow(applicationContext).first()
            }.getOrDefault(true)
            if (enabled) showNotification(title, body, type, referenceId, roleTarget, notificationId, timestamp)
        }
    }

    private fun showNotification(
        title: String,
        body: String,
        type: String?,
        referenceId: String?,
        roleTarget: String?,
        notificationId: Int?,
        fallbackId: Long
    ) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) return

        val channelId = NotificationChannels.USER_NOTIFICATIONS
        NotificationChannels.create(this)

        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
            putExtra(NotificationData.EXTRA_TYPE, type)
            putExtra(NotificationData.EXTRA_PROPERTY_ID, referenceId)
            putExtra(NotificationData.EXTRA_NOTIFICATION_ID, notificationId?.toString())
            putExtra(NotificationData.EXTRA_ROLE_TARGET, roleTarget)
        }
        val pendingIntent = PendingIntent.getActivity(
            this,
            (notificationId?.toLong() ?: fallbackId).hashCode(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val notification = NotificationCompat.Builder(this, channelId)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .build()

        NotificationManagerCompat.from(this).notify(
            notificationId ?: fallbackId.hashCode(),
            notification
        )
    }
}
