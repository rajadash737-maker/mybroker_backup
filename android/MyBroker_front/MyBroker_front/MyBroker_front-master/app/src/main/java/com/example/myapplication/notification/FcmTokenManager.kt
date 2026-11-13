package com.example.myapplication.notification

import android.content.Context
import android.util.Log
import com.example.myapplication.network.ApiClient
import com.example.myapplication.network.FcmTokenRequest
import com.example.myapplication.network.SessionManager
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

object FcmTokenManager {
    fun refreshToken(context: Context) {
        FirebaseMessaging.getInstance().token.addOnSuccessListener { token ->
            val cleaned = token.trim()
            if (cleaned.isEmpty()) return@addOnSuccessListener
            val session = SessionManager(context.applicationContext)
            session.saveFcmToken(cleaned)
            tryRegisterPendingToken(context.applicationContext)
        }.addOnFailureListener { Log.w("FCM", "Unable to refresh FCM token", it) }
    }

    fun onNewToken(context: Context, token: String) {
        val cleaned = token.trim()
        if (cleaned.isEmpty()) return
        SessionManager(context.applicationContext).saveFcmToken(cleaned)
        tryRegisterPendingToken(context.applicationContext)
    }

    fun tryRegisterPendingToken(context: Context, force: Boolean = false) {
        val session = SessionManager(context.applicationContext)
        val token = session.getFcmToken().orEmpty()
        if (token.isBlank() || session.getAccessToken().isNullOrBlank()) return
        if (!force && session.getFcmTokenSynced() == token) return
        CoroutineScope(Dispatchers.IO).launch {
            runCatching {
                ApiClient.init(context.applicationContext)
                ApiClient.apiService.registerFcmToken(FcmTokenRequest(token))
            }.onSuccess { response ->
                if (response.isSuccessful) session.saveFcmTokenSynced(token)
            }.onFailure { Log.w("FCM", "Unable to register FCM token", it) }
        }
    }
}
