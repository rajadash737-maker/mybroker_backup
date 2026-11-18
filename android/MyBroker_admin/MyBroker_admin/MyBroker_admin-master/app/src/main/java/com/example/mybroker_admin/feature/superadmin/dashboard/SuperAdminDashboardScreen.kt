package com.example.mybroker_admin.feature.superadmin.dashboard

import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AttachMoney
import androidx.compose.material.icons.filled.Group
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Pending
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import com.example.mybroker_admin.core.navigation.Routes
import com.example.mybroker_admin.core.session.SessionManager
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.feature.superadmin.dashboard.components.StatCard
import com.example.mybroker_admin.feature.common.PullToRefreshBox
import com.example.mybroker_admin.feature.common.NotificationActionButton
import com.example.mybroker_admin.notification.NotificationStore
import java.text.NumberFormat
import java.util.Locale
import androidx.compose.material3.AlertDialog

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SuperAdminDashboardScreen(navController: NavHostController) {
    val dashboardViewModel = viewModel<SuperAdminDashboardViewModel>()
    val state by dashboardViewModel.state.collectAsState()
    val formatter = NumberFormat.getNumberInstance(Locale.Builder().setLanguage("en").setRegion("IN").build())
    val context = LocalContext.current
    val notificationVersion by NotificationStore.version.collectAsState()
    val unreadCount = remember(notificationVersion) {
        NotificationStore.unreadCount(context)
    }
    val showLogoutDialog = remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Super Admin Dashboard") },
                actions = {
                    NotificationActionButton(
                        onClick = { navController.navigate(Routes.NOTIFICATIONS) },
                        unreadCount = unreadCount
                    )
                    TextButton(onClick = { showLogoutDialog.value = true }) {
                        Text("Logout")
                    }
                }
            )
        }
    ) { padding ->

        PullToRefreshBox(
            isRefreshing = state.isLoading,
            onRefresh = { dashboardViewModel.refresh() },
            modifier = Modifier
                .padding(padding)
                .padding(16.dp)
        ) {
            LazyColumn(
                modifier = Modifier.fillMaxWidth()
            ) {

                item {
                    Text(
                        "Overview",
                        style = MaterialTheme.typography.titleLarge
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                }

                item {
                    Row {
                        StatCard(
                            title = "Total Listings",
                            value = state.totalListings.toString(),
                            icon = Icons.Default.Home,
                            modifier = Modifier.weight(1f),
                            onClick = { navController.navigate(Routes.SUPER_ADMIN_LISTINGS) }
                        )

                        Spacer(modifier = Modifier.width(12.dp))
                        StatCard(
                            title = "Pending",
                            value = state.pendingAdminReview?.toString()
                                ?: if (state.isPendingCountLoading) "..." else "N/A",
                            icon = Icons.Default.Pending,
                            modifier = Modifier.weight(1f),
                            onClick = { navController.navigate(Routes.SUPER_ADMIN_LISTINGS) }
                        )

                    }
                }

                state.pendingCountErrorMessage?.let { pendingError ->
                    item {
                        Text(
                            text = pendingError,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.error
                        )
                    }
                }

                item { Spacer(modifier = Modifier.height(12.dp)) }

                item {
                    androidx.compose.material3.Button(
                        onClick = { navController.navigate(Routes.SUPER_ADMIN_SITE_VISIT_AUDIT) },
                        modifier = Modifier.fillMaxWidth()
                    ) { Text("Site Visit Audit") }
                }

                item {
                    Row {
                        StatCard(
                            title = "Staff",
                            value = "6",
                            icon = Icons.Default.Group,
                            modifier = Modifier.weight(1f),
                            onClick = { navController.navigate(Routes.STAFF_ANALYTICS) }
                        )

                        Spacer(modifier = Modifier.width(12.dp))
                        StatCard(
                            title = "Revenue",
                            value = "?${formatter.format(state.totalRevenue)}",
                            icon = Icons.Default.AttachMoney,
                            modifier = Modifier.weight(1f),
                            onClick = { navController.navigate(Routes.SUPER_ADMIN_REVENUE) }
                        )

                    }
                }

                item { Spacer(modifier = Modifier.height(24.dp)) }

                item {
                    Row {
                        StatCard(
                            title = "Ratings",
                            value = "View",
                            icon = Icons.Default.Star,
                            modifier = Modifier.weight(1f),
                            onClick = { navController.navigate(Routes.ADMIN_RATINGS) }
                        )
                    }
                }

                item { Spacer(modifier = Modifier.height(24.dp)) }

                item {
                    Text(
                        "Quick Actions",
                        style = MaterialTheme.typography.titleLarge
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                }

                item {
                    androidx.compose.material3.Button(
                        onClick = { navController.navigate(Routes.STAFF_MANAGEMENT) },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Manage Staff")
                    }
                }

                item { Spacer(modifier = Modifier.height(8.dp)) }

                item {
                    androidx.compose.material3.Button(
                        onClick = { },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("View All Listings")
                    }
                }

                item { Spacer(modifier = Modifier.height(8.dp)) }

                item {
                    androidx.compose.material3.Button(
                        onClick = { navController.navigate(Routes.SOCIAL_LINKS) },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Social Links")
                    }
                }

                item { Spacer(modifier = Modifier.height(8.dp)) }

                item {
                    androidx.compose.material3.Button(
                        onClick = { navController.navigate(Routes.BANNERS) },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Home Banners")
                    }
                }

                item { Spacer(modifier = Modifier.height(8.dp)) }

                item {
                    androidx.compose.material3.Button(
                        onClick = { navController.navigate(Routes.PROCESSING_FEES) },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Processing Fees")
                    }
                }
            }
        }
    }

    if (showLogoutDialog.value) {
        AlertDialog(
            onDismissRequest = { showLogoutDialog.value = false },
            title = { Text("Logout") },
            text = { Text("Are you sure you want to logout from this account?") },
            confirmButton = {
                TextButton(
                    onClick = {
                        showLogoutDialog.value = false
                        SessionManager.clear()
                        ApiClient.setAccessToken(null)
                        NotificationStore.clear(context)
                        navController.navigate(Routes.LOGIN) {
                            popUpTo(Routes.LOGIN) { inclusive = true }
                            launchSingleTop = true
                        }
                    }
                ) {
                    Text("Logout")
                }
            },
            dismissButton = {
                TextButton(onClick = { showLogoutDialog.value = false }) {
                    Text("Cancel")
                }
            }
        )
    }
}
