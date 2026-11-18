package com.example.myapplication

import android.app.Application
import com.example.myapplication.notification.NotificationChannels

class MyBrokerApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        NotificationChannels.create(this)
    }
}
