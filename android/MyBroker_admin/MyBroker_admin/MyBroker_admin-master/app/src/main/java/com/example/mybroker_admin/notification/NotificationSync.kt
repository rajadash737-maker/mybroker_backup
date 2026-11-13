package com.example.mybroker_admin.notification

import android.content.Context
import android.util.Log
import com.example.mybroker_admin.core.session.SessionManager
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.remote.dto.NotificationDto
import com.example.mybroker_admin.data.remote.dto.NotificationReadRequestDto
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.time.Instant
import java.time.LocalDateTime
import java.time.ZoneId

object NotificationSync {
    private const val TAG = "NOTIF_SYNC"

    fun refreshFromServer(context: Context) {
        if (SessionManager.accessToken.isNullOrBlank()) return
        CoroutineScope(Dispatchers.IO).launch {
            runCatching {
                ApiClient.notificationApi.listNotifications()
            }.onSuccess { resp ->
                val items = resp.items.map { it.toItem() }
                NotificationStore.upsertAll(context, items)
            }.onFailure { err ->
                Log.w(TAG, "Failed to refresh notifications", err)
            }
        }
    }

    fun markRead(context: Context, notificationIds: List<Int> = emptyList(), referenceIds: List<String> = emptyList()) {
        if (SessionManager.accessToken.isNullOrBlank()) return
        if (notificationIds.isEmpty() && referenceIds.isEmpty()) return
        CoroutineScope(Dispatchers.IO).launch {
            runCatching {
                ApiClient.notificationApi.markRead(
                    NotificationReadRequestDto(
                        notificationIds = notificationIds,
                        referenceIds = referenceIds
                    )
                )
            }.onFailure { err ->
                Log.w(TAG, "Failed to sync read state", err)
            }
        }
    }

    fun markAllRead(context: Context) {
        if (SessionManager.accessToken.isNullOrBlank()) return
        CoroutineScope(Dispatchers.IO).launch {
            runCatching {
                ApiClient.notificationApi.markRead(
                    NotificationReadRequestDto(markAll = true)
                )
            }.onFailure { err ->
                Log.w(TAG, "Failed to mark all read", err)
            }
        }
    }

    private fun NotificationDto.toItem(): NotificationItem {
        val created = createdAt?.let { parseTimestamp(it) } ?: System.currentTimeMillis()
        return NotificationItem(
            id = id,
            title = title,
            body = body,
            type = type,
            propertyId = referenceId,
            timestamp = created,
            isRead = isRead
        )
    }

    private fun parseTimestamp(value: String): Long {
        val instant = runCatching { Instant.parse(value) }.getOrNull()
        if (instant != null) return instant.toEpochMilli()
        val local = runCatching { LocalDateTime.parse(value) }.getOrNull()
        return local?.atZone(ZoneId.systemDefault())?.toInstant()?.toEpochMilli()
            ?: System.currentTimeMillis()
    }
}
