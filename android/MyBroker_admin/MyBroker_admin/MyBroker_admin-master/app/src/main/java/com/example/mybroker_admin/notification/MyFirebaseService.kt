package com.example.mybroker_admin.notification

import android.util.Log
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

class MyFirebaseService : FirebaseMessagingService() {
    override fun onMessageReceived(message: RemoteMessage) {
        val data = NotificationData.fromRemoteMessage(message)
        val title = message.data["title"]
            ?: message.notification?.title
            ?: "New Property Uploaded"
        val body = message.data["body"]
            ?: message.notification?.body
            ?: "A new property needs verification"

        NotificationHelper.showNotification(
            context = this,
            title = title,
            body = body,
            data = data
        )

        NotificationStore.add(
            context = this,
            item = NotificationItem(
                id = data.notificationId?.toIntOrNull(),
                title = title,
                body = body,
                type = data.type,
                propertyId = data.propertyId,
                timestamp = System.currentTimeMillis()
            )
        )
    }

    override fun onNewToken(token: String) {
        Log.d("FCM", "New token: $token")
        FcmTokenManager.onNewToken(this, token)
    }
}
