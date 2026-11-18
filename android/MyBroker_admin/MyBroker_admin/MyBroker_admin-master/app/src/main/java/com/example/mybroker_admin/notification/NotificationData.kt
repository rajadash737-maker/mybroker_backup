package com.example.mybroker_admin.notification

import android.content.Intent
import com.google.firebase.messaging.RemoteMessage

data class NotificationData(
    val notificationId: String?,
    val type: String?,
    val propertyId: String?,
    val roleTarget: String?
) {
    companion object {
        const val TYPE_LAND_SUBMITTED = "LAND_SUBMITTED"
        const val TYPE_LAND_VERIFIED = "LAND_VERIFIED"
        const val TYPE_LAND_REJECTED = "LAND_REJECTED"
        const val TYPE_CASE_ASSIGNED = "CASE_ASSIGNED"
        const val TYPE_FIELD_VISIT_APPROVED = "FIELD_VISIT_APPROVED"
        const val TYPE_FIELD_VISIT_REJECTED = "FIELD_VISIT_REJECTED"
        const val TYPE_FINAL_APPROVAL_APPROVED = "FINAL_APPROVAL_APPROVED"
        const val TYPE_FINAL_APPROVAL_REJECTED = "FINAL_APPROVAL_REJECTED"
        const val TYPE_LISTING_LOCKED_FOR_ADMIN = "LISTING_LOCKED_FOR_ADMIN"
        const val TYPE_BOOKING_PAYMENT_SUCCESS = "BOOKING_PAYMENT_SUCCESS"
        const val TYPE_SITE_VISIT_ASSIGNED = "SITE_VISIT_ASSIGNED"
        const val TYPE_SITE_VISIT_ASSIGNMENT_REMOVED = "SITE_VISIT_ASSIGNMENT_REMOVED"
        const val TYPE_SITE_VISIT_COMPLETED = "SITE_VISIT_COMPLETED"
        const val TYPE_SITE_VISIT_COMPLETION_CODE_READY = "SITE_VISIT_COMPLETION_CODE_READY"
        const val TYPE_REGISTRY_SCHEDULED = "REGISTRY_SCHEDULED"
        const val TYPE_REGISTRY_IN_PROCESS = "REGISTRY_IN_PROCESS"
        const val TYPE_REGISTRY_DONE = "REGISTRY_DONE"
        const val TYPE_REGISTRY_SOLD = "REGISTRY_SOLD"
        const val EXTRA_TYPE = "extra_notification_type"
        const val EXTRA_PROPERTY_ID = "extra_property_id"
        const val EXTRA_NOTIFICATION_ID = "extra_notification_id"
        const val EXTRA_ROLE_TARGET = "extra_role_target"

        fun fromRemoteMessage(message: RemoteMessage): NotificationData {
            val data = message.data
            return NotificationData(
                notificationId = data["notification_id"],
                type = data["type"],
                propertyId = data["reference_id"] ?: data["property_id"],
                roleTarget = data["role_target"]
            )
        }

        fun fromIntent(intent: Intent?): NotificationData? {
            if (intent == null) return null
            val type = intent.getStringExtra(EXTRA_TYPE)
            val propertyId = intent.getStringExtra(EXTRA_PROPERTY_ID)
            val notificationId = intent.getStringExtra(EXTRA_NOTIFICATION_ID)
            val roleTarget = intent.getStringExtra(EXTRA_ROLE_TARGET)
            if (type.isNullOrBlank() && propertyId.isNullOrBlank()) return null
            return NotificationData(
                notificationId = notificationId,
                type = type,
                propertyId = propertyId,
                roleTarget = roleTarget
            )
        }
    }
}

