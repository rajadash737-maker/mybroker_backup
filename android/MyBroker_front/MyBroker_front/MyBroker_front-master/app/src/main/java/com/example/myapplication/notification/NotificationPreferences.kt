package com.example.myapplication.notification

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.notificationPreferencesDataStore by preferencesDataStore(
    name = "notification_preferences"
)

object NotificationPreferences {
    private val notificationsEnabledKey = booleanPreferencesKey("notifications_enabled")

    fun notificationsEnabledFlow(context: Context): Flow<Boolean> =
        context.notificationPreferencesDataStore.data.map { preferences ->
            preferences[notificationsEnabledKey] ?: true
        }

    suspend fun setNotificationsEnabled(context: Context, enabled: Boolean) {
        context.notificationPreferencesDataStore.edit { preferences ->
            preferences[notificationsEnabledKey] = enabled
        }
    }
}
