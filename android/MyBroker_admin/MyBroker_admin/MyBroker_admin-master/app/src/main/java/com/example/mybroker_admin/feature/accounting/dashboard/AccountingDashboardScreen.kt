// AccountingDashboardScreen.kt
package com.example.mybroker_admin.feature.accounting.dashboard

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import coil.compose.AsyncImage
import com.example.mybroker_admin.core.navigation.Routes
import com.example.mybroker_admin.feature.accounting.dashboard.components.AccountingRevenueRangeType
import com.example.mybroker_admin.feature.accounting.dashboard.components.StatCard
import com.example.mybroker_admin.feature.common.PullToRefreshBox
import com.example.mybroker_admin.feature.common.NotificationActionButton
import com.example.mybroker_admin.notification.NotificationStore
import java.text.DecimalFormat

@Composable
fun AccountingDashboardScreen(
    navController: NavController,
    viewModel: AccountingDashboardViewModel = viewModel()
) {
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current
    val notificationVersion by NotificationStore.version.collectAsState()
    val unreadCount = remember(notificationVersion) {
        NotificationStore.unreadCount(context)
    }

    PullToRefreshBox(
        isRefreshing = state.isLoading,
        onRefresh = { viewModel.refresh() },
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "Accounting Dashboard",
                        style = MaterialTheme.typography.headlineMedium
                    )
                    Text(
                        text = "Hi, ${state.accountantName}",
                        style = MaterialTheme.typography.bodyMedium
                    )
                }

                Row(verticalAlignment = Alignment.CenterVertically) {
                    NotificationActionButton(
                        onClick = { navController.navigate(Routes.NOTIFICATIONS) },
                        unreadCount = unreadCount
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    if (!state.profileImageUrl.isNullOrBlank()) {
                        AsyncImage(
                            model = state.profileImageUrl,
                            contentDescription = "Accounting Profile",
                            modifier = Modifier
                                .size(46.dp)
                                .clip(CircleShape)
                                .background(MaterialTheme.colorScheme.surfaceVariant)
                                .clickable { navController.navigate(Routes.PROFILE) },
                            contentScale = ContentScale.Crop
                        )
                    } else {
                        Icon(
                            imageVector = Icons.Default.AccountCircle,
                            contentDescription = "Default Profile",
                            modifier = Modifier
                                .size(46.dp)
                                .clickable { navController.navigate(Routes.PROFILE) }
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            Text("Revenue Filters", style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(8.dp))
            Row(
                modifier = Modifier.horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                FilterChip(
                    selected = state.rangeType == AccountingRevenueRangeType.ALL,
                    onClick = { viewModel.setRange(AccountingRevenueRangeType.ALL) },
                    label = { Text("All") }
                )
                FilterChip(
                    selected = state.rangeType == AccountingRevenueRangeType.TODAY,
                    onClick = { viewModel.setRange(AccountingRevenueRangeType.TODAY) },
                    label = { Text("Today") }
                )
                FilterChip(
                    selected = state.rangeType == AccountingRevenueRangeType.WEEK,
                    onClick = { viewModel.setRange(AccountingRevenueRangeType.WEEK) },
                    label = { Text("Week") }
                )
                FilterChip(
                    selected = state.rangeType == AccountingRevenueRangeType.MONTH,
                    onClick = { viewModel.setRange(AccountingRevenueRangeType.MONTH) },
                    label = { Text("Month") }
                )
                FilterChip(
                    selected = state.rangeType == AccountingRevenueRangeType.CUSTOM,
                    onClick = { viewModel.setRange(AccountingRevenueRangeType.CUSTOM) },
                    label = { Text("Custom") }
                )
            }

            if (state.rangeType == AccountingRevenueRangeType.CUSTOM) {
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(
                    value = state.customStart,
                    onValueChange = viewModel::updateCustomStart,
                    label = { Text("Start (YYYY-MM-DD)") },
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(
                    value = state.customEnd,
                    onValueChange = viewModel::updateCustomEnd,
                    label = { Text("End (YYYY-MM-DD)") },
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(8.dp))
                Button(
                    onClick = viewModel::applyCustomRange,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Apply Range")
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            val currency = "\u20B9"
            val revenueText = DecimalFormat("#,##0.##").format(state.totalRevenue)
            StatCard("Total Revenue", "$currency $revenueText")
            StatCard("Pending Payments", state.pendingPayments.toString())
            StatCard(
                title = "Transactions List",
                value = state.completedTransactions.toString(),
                modifier = Modifier.clickable {
                    navController.navigate(Routes.ACCOUNTING_COMPLETED_TRANSACTIONS)
                }
            )
            StatCard(
                title = "Refund Requests",
                value = state.pendingRefunds.toString(),
                modifier = Modifier.clickable {
                    navController.navigate(Routes.ACCOUNTING_REFUND_LIST)
                }
            )
            StatCard(
                title = "Webhook Logs",
                value = state.webhookLogCount.toString(),
                modifier = Modifier.clickable {
                    navController.navigate(Routes.WEBHOOK_LOGS)
                }
            )
        }
    }
}
