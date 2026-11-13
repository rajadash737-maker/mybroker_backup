package com.example.mybroker_admin.notification

import android.content.Context
import android.util.Log
import com.example.mybroker_admin.core.session.SessionManager
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.remote.dto.FcmTokenRequestDto
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

object FcmTokenManager {
    private const val TAG = "FCM"

    fun refreshToken(context: Context) {
        FirebaseMessaging.getInstance().token
            .addOnCompleteListener { task ->
                if (task.isSuccessful) {
                    val token = task.result?.trim().orEmpty()
                    Log.d("FCM_DEBUG", "Token: $token")
                    if (token.isNotEmpty()) {
                        onNewToken(context, token)
                    } else {
                        Log.w("FCM_DEBUG", "Token empty after fetch")
                    }
                } else {
                    Log.e("FCM_DEBUG", "Token failed", task.exception)
                }
            }
    }

    fun onNewToken(context: Context, token: String) {
        val cleaned = token.trim()
        if (cleaned.isEmpty()) {
            Log.w(TAG, "Token empty after trim; skipping")
            return
        }
        SessionManager.saveFcmToken(cleaned)
        tryRegisterPendingToken()
    }

    fun tryRegisterPendingToken(force: Boolean = false) {
        val token = SessionManager.fcmToken?.trim().orEmpty()
        val accessToken = SessionManager.accessToken
        if (token.isEmpty() || accessToken.isNullOrBlank()) {
            Log.d("FCM_DEBUG", "Token sync skipped (token or access token missing)")
            return
        }
        if (!force && SessionManager.fcmTokenSynced == token) {
            Log.d("FCM_DEBUG", "Token already synced; skipping")
            return
        }

        CoroutineScope(Dispatchers.IO).launch {
            runCatching {
                Log.d("FCM_DEBUG", "Sending token to backend")
                ApiClient.profileApi.registerFcmToken(FcmTokenRequestDto(token))
            }.onSuccess {
                SessionManager.saveFcmTokenSynced(token)
                Log.d("FCM_DEBUG", "FCM token synced")
            }.onFailure { err ->
                Log.w("FCM_DEBUG", "Failed to sync FCM token", err)
            }
        }
    }
}
