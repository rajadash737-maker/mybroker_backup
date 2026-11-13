package com.example.mybroker_admin.feature.admin.dashboard.presentation

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.example.mybroker_admin.feature.admin.dashboard.model.DashboardStats
import com.example.mybroker_admin.feature.admin.dashboard.presentation.components.StatCard
import com.example.mybroker_admin.feature.common.PullToRefreshBox
import com.example.mybroker_admin.feature.common.NotificationActionButton


@Composable
fun AdminDashboardScreen(
    stats: DashboardStats,
    isRefreshing: Boolean,
    unreadCount: Int,
    onRefresh: () -> Unit,
    onPendingClick: () -> Unit,
    onAssignedClick: () -> Unit,
    onFieldVerifiedClick: () -> Unit,
    onLiveClick: () -> Unit,
    onLockedClick: () -> Unit,
    onBookedClick: () -> Unit,
    onSoldClick: () -> Unit,
    onRegistryPendingClick: () -> Unit,
    onRejectedClick: () -> Unit,
    onCancelRefundClick: () -> Unit,
    onProfileClick: () -> Unit,
    onNotificationsClick: () -> Unit
) {
    PullToRefreshBox(
        isRefreshing = isRefreshing,
        onRefresh = onRefresh,
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {

            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = "Admin Dashboard",
                            style = MaterialTheme.typography.headlineMedium
                        )
                        Text(text = "Hi, ${stats.adminName}", style = MaterialTheme.typography.bodyMedium)

                    }

                    Row(verticalAlignment = Alignment.CenterVertically) {
                        NotificationActionButton(
                            onClick = onNotificationsClick,
                            unreadCount = unreadCount
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        if (!stats.profileImageUrl.isNullOrBlank()) {
                            AsyncImage(
                                model = stats.profileImageUrl,
                                contentDescription = "Admin Profile",
                                modifier = Modifier
                                    .size(48.dp)
                                    .clip(CircleShape)
                                    .background(MaterialTheme.colorScheme.surfaceVariant)
                                    .clickable { onProfileClick() },
                                contentScale = ContentScale.Crop
                            )
                        } else {
                            Icon(
                                imageVector = Icons.Default.AccountCircle,
                                contentDescription = "Default Profile",
                                modifier = Modifier
                                    .size(48.dp)
                                    .clickable { onProfileClick() }
                            )
                        }
                    }

                }
            }

            item {
                Text(
                    text = "Workflow Overview",
                    style = MaterialTheme.typography.titleMedium
                )
            }

            item {
                StatCard(
                    "Pending Admin Review",
                    stats.pendingCount,
                    onPendingClick) }

            item {
                StatCard(
                    "Assigned To Field Officer",
                    stats.assignedCount,
                    onAssignedClick) }

            item {
                StatCard(
                    "Field Verified (Final Approval)",
                    stats.fieldVerifiedCount,
                    onFieldVerifiedClick) }

            item { StatCard("Live Listings", stats.liveCount, onLiveClick) }
            item { StatCard("Locked Listings", stats.lockedCount, onLockedClick) }
            item { StatCard("Booked Listings", stats.bookedCount, onBookedClick) }
            item { StatCard("Sold Listings", stats.soldCount, onSoldClick) }
            item { StatCard("Pending Registry Verification", stats.pendingRegistryVerificationCount, onRegistryPendingClick) }
            item { StatCard("Rejected Listings", stats.rejectedCount, onRejectedClick) }
            item {
                StatCard(
                    title = "Cancel & Refund Management",
                    count = stats.cancelPendingCount,
                    onClick = onCancelRefundClick
                )
            }

            item {
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = "Recent Activity",
                    style = MaterialTheme.typography.titleMedium
                )
            }


            items((0..4).toList()) { index ->
                Text(text = "Listing ID: LST-10$index")
            }
        }
    }
}
