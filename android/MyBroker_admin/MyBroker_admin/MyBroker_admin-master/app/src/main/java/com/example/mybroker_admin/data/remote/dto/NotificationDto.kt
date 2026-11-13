package com.example.mybroker_admin.data.remote.dto

import com.google.gson.annotations.SerializedName

data class NotificationDto(
    val id: Int,
    val title: String,
    val body: String,
    val type: String,
    @SerializedName("role_target")
    val roleTarget: String? = null,
    @SerializedName("reference_id")
    val referenceId: String? = null,
    @SerializedName("is_read")
    val isRead: Boolean = false,
    @SerializedName("created_at")
    val createdAt: String? = null
)

data class NotificationListResponseDto(
    val total: Int = 0,
    val items: List<NotificationDto> = emptyList()
)

data class NotificationReadRequestDto(
    @SerializedName("notification_ids")
    val notificationIds: List<Int> = emptyList(),
    @SerializedName("reference_ids")
    val referenceIds: List<String> = emptyList(),
    @SerializedName("mark_all")
    val markAll: Boolean = false
)
