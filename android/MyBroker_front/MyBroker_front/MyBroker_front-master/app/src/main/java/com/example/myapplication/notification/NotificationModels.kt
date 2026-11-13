package com.example.myapplication.notification

import android.content.Intent

data class NotificationItem(
    val id: Int? = null,
    val title: String,
    val body: String,
    val type: String? = null,
    val referenceId: String? = null,
    val roleTarget: String? = null,
    val timestamp: Long,
    val isRead: Boolean = false
)

data class NotificationData(
    val notificationId: String?,
    val type: String?,
    val propertyId: String?,
    val roleTarget: String?
) {
    companion object {
        const val EXTRA_TYPE = "extra_notification_type"
        const val EXTRA_PROPERTY_ID = "extra_property_id"
        const val EXTRA_NOTIFICATION_ID = "extra_notification_id"
        const val EXTRA_ROLE_TARGET = "extra_role_target"

        fun fromIntent(intent: Intent?): NotificationData? {
            if (intent == null) return null

            val data = NotificationData(
                notificationId = intent.getStringExtra(EXTRA_NOTIFICATION_ID),
                type = intent.getStringExtra(EXTRA_TYPE),
                propertyId = intent.getStringExtra(EXTRA_PROPERTY_ID),
                roleTarget = intent.getStringExtra(EXTRA_ROLE_TARGET)
            )
            return data.takeIf { !it.type.isNullOrBlank() || !it.propertyId.isNullOrBlank() }
        }
    }
}
