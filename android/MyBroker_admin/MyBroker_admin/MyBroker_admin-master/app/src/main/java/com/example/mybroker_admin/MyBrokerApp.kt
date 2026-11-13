package com.example.mybroker_admin



import android.app.Application
import com.example.mybroker_admin.data.remote.ApiClient
import dagger.hilt.android.HiltAndroidApp
import com.example.mybroker_admin.core.session.SessionManager
import com.example.mybroker_admin.notification.FcmTokenManager
import com.example.mybroker_admin.notification.NotificationStore
import com.example.mybroker_admin.notification.NotificationSync


@HiltAndroidApp
class MyBrokerApp : Application() {
    override fun onCreate() {
        super.onCreate()
        SessionManager.init(this)
        ApiClient.setAccessToken(SessionManager.accessToken)
        FcmTokenManager.refreshToken(this)
        FcmTokenManager.tryRegisterPendingToken()
        NotificationSync.refreshFromServer(this)
        NotificationStore.cleanupDuplicates(this)

    }
}
