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
                    if (token.isNotEmpty()) {
                        onNewToken(context, token)
                    } else {
                        Log.w(TAG, "Token refresh returned an empty value")
                    }
                } else {
                    Log.w(TAG, "Token refresh failed (${task.exception?.javaClass?.simpleName ?: "unknown"})")
                }
            }
    }

    fun onNewToken(context: Context, token: String) {
        val cleaned = token.trim()
        if (cleaned.isEmpty()) {
            Log.w(TAG, "Token refresh returned an empty value")
            return
        }
        SessionManager.saveFcmToken(cleaned)
        tryRegisterPendingToken()
    }

    fun tryRegisterPendingToken(force: Boolean = false) {
        val token = SessionManager.fcmToken?.trim().orEmpty()
        val accessToken = SessionManager.accessToken
        if (token.isEmpty() || accessToken.isNullOrBlank()) {
            return
        }
        if (!force && SessionManager.fcmTokenSynced == token) {
            return
        }

        CoroutineScope(Dispatchers.IO).launch {
            runCatching {
                ApiClient.profileApi.registerFcmToken(FcmTokenRequestDto(token))
            }.onSuccess {
                SessionManager.saveFcmTokenSynced(token)
            }.onFailure { err ->
                Log.w(TAG, "Token registration failed (${err.javaClass.simpleName})")
            }
        }
    }
}
