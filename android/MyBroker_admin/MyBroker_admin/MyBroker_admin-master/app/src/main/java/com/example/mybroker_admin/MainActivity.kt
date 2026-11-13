package com.example.mybroker_admin

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.navigation.compose.rememberNavController
import dagger.hilt.android.AndroidEntryPoint

import com.example.mybroker_admin.core.theme.Mybroker_adminTheme
import com.example.mybroker_admin.core.navigation.RootNavGraph
import com.example.mybroker_admin.core.session.SessionManager
import com.example.mybroker_admin.notification.NotificationData
import com.example.mybroker_admin.notification.NotificationRoutes
import com.example.mybroker_admin.notification.NotificationStore

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    private var notificationData by mutableStateOf<NotificationData?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestNotificationPermissionIfNeeded()
        notificationData = NotificationData.fromIntent(intent)

        setContent {
            Mybroker_adminTheme {

                val navController = rememberNavController()

                LaunchedEffect(notificationData) {
                    val data = notificationData ?: return@LaunchedEffect
                    data.propertyId?.trim()?.takeIf { it.isNotEmpty() }?.let { propertyId ->
                        NotificationStore.markReadByPropertyId(this@MainActivity, propertyId)
                    }
                    val route = NotificationRoutes.routeForNotification(
                        type = data.type,
                        referenceId = data.propertyId,
                        role = SessionManager.currentUserRole
                    )
                    if (route != null) {
                        navController.navigate(route) {
                            launchSingleTop = true
                        }
                    }
                }

                RootNavGraph(navController = navController)

            }
        }
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        notificationData = NotificationData.fromIntent(intent)
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
        val granted = ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.POST_NOTIFICATIONS
        ) == PackageManager.PERMISSION_GRANTED
        if (!granted) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                1001
            )
        }
    }
}
