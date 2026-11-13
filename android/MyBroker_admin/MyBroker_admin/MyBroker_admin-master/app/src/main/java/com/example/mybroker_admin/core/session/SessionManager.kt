package com.example.mybroker_admin.core.session

import android.content.Context
import android.content.SharedPreferences

object SessionManager {
    private const val PREF_NAME = "mybroker_admin_session"
    private const val KEY_ACCESS = "access_token"
    private const val KEY_REFRESH = "refresh_token"
    private const val KEY_ROLE = "current_role"
    private const val KEY_USER_NAME = "current_user_name"
    private const val KEY_USER_EMAIL = "current_user_email"
    private const val KEY_DASHBOARD = "dashboard_key"
    private const val KEY_FCM_TOKEN = "fcm_token"
    private const val KEY_FCM_TOKEN_SYNCED = "fcm_token_synced"

    private var initialized = false
    private lateinit var prefs: SharedPreferences

    var accessToken: String? = null
        private set
    var refreshToken: String? = null
        private set
    var currentUserRole: String? = null
        private set
    var currentUserName: String? = null
        private set
    var currentUserEmail: String? = null
        private set
    var dashboardKey: String? = null
        private set
    var fcmToken: String? = null
        private set
    var fcmTokenSynced: String? = null
        private set

    fun init(context: Context) {
        if (initialized) return
        prefs = context.applicationContext.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        accessToken = prefs.getString(KEY_ACCESS, null)
        refreshToken = prefs.getString(KEY_REFRESH, null)
        currentUserRole = prefs.getString(KEY_ROLE, null)
        currentUserName = prefs.getString(KEY_USER_NAME, null)
        currentUserEmail = prefs.getString(KEY_USER_EMAIL, null)
        dashboardKey = prefs.getString(KEY_DASHBOARD, null)
        fcmToken = prefs.getString(KEY_FCM_TOKEN, null)
        fcmTokenSynced = prefs.getString(KEY_FCM_TOKEN_SYNCED, null)
        initialized = true
    }

    fun saveLogin(
        access: String?,
        refresh: String?,
        role: String?,
        dashboard: String?,
        fullName: String? = currentUserName,
        email: String? = currentUserEmail
    ) {
        accessToken = access
        refreshToken = refresh
        currentUserRole = role
        currentUserName = fullName
        currentUserEmail = email
        dashboardKey = dashboard
        if (initialized) {
            prefs.edit()
                .putString(KEY_ACCESS, access)
                .putString(KEY_REFRESH, refresh)
                .putString(KEY_ROLE, role)
                .putString(KEY_USER_NAME, fullName)
                .putString(KEY_USER_EMAIL, email)
                .putString(KEY_DASHBOARD, dashboard)
                .apply()
        }
    }

    fun updateUserIdentity(
        fullName: String? = currentUserName,
        email: String? = currentUserEmail,
        role: String? = currentUserRole
    ) {
        currentUserName = fullName
        currentUserEmail = email
        currentUserRole = role
        if (initialized) {
            prefs.edit()
                .putString(KEY_USER_NAME, fullName)
                .putString(KEY_USER_EMAIL, email)
                .putString(KEY_ROLE, role)
                .apply()
        }
    }

    fun clear() {
        accessToken = null
        refreshToken = null
        currentUserRole = null
        currentUserName = null
        currentUserEmail = null
        dashboardKey = null
        fcmToken = null
        fcmTokenSynced = null
        if (initialized) {
            prefs.edit().clear().apply()
        }
    }

    fun saveFcmToken(token: String?) {
        fcmToken = token
        if (initialized) {
            prefs.edit().putString(KEY_FCM_TOKEN, token).apply()
        }
    }

    fun saveFcmTokenSynced(token: String?) {
        fcmTokenSynced = token
        if (initialized) {
            prefs.edit().putString(KEY_FCM_TOKEN_SYNCED, token).apply()
        }
    }
}
