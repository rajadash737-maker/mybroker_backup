package com.example.myapplication.notification

import android.content.Context
import com.example.myapplication.network.ApiClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

object NotificationSync {
    fun refreshFromServer(context: Context) {
        CoroutineScope(Dispatchers.IO).launch {
            runCatching {
                ApiClient.init(context.applicationContext)
                val response = ApiClient.apiService.listNotifications()
                if (response.isSuccessful) response.body()?.items?.let { NotificationStore.upsertAll(context, it) }
            }
        }
    }

    fun markRead(context: Context, notificationIds: List<Int> = emptyList(), referenceIds: List<String> = emptyList()) {
        CoroutineScope(Dispatchers.IO).launch {
            runCatching {
                ApiClient.init(context.applicationContext)
                ApiClient.apiService.markNotificationsRead(NotificationReadRequestDto(notificationIds, referenceIds))
            }
        }
    }

    fun markAllRead(context: Context) {
        CoroutineScope(Dispatchers.IO).launch {
            runCatching {
                ApiClient.init(context.applicationContext)
                ApiClient.apiService.markNotificationsRead(NotificationReadRequestDto(markAll = true))
                    .takeIf { it.isSuccessful }?.body()?.items?.let { NotificationStore.upsertAll(context, it) }
            }
        }
    }
}
