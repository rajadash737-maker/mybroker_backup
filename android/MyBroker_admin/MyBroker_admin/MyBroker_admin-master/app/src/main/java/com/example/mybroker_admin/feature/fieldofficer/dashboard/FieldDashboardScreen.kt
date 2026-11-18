package com.example.mybroker_admin.feature.fieldofficer.dashboard

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import coil.compose.SubcomposeAsyncImage
import coil.request.ImageRequest
import com.example.mybroker_admin.core.navigation.Routes
import com.example.mybroker_admin.feature.fieldofficer.dashboard.components.ActiveCaseCard
import com.example.mybroker_admin.feature.fieldofficer.dashboard.components.StatCard
import com.example.mybroker_admin.feature.common.PullToRefreshBox
import com.example.mybroker_admin.feature.common.NotificationActionButton
import com.example.mybroker_admin.feature.registry.RegistryDashboardViewModel
import com.example.mybroker_admin.feature.registry.components.RegistryUpcomingCard
import com.example.mybroker_admin.notification.NotificationStore

@Composable
fun FieldDashboardScreen(
    navController: NavController,
    viewModel: FieldDashboardViewModel = viewModel()
) {
    val state by viewModel.uiState.collectAsState()
    val registryViewModel: RegistryDashboardViewModel = viewModel()
    val registryState by registryViewModel.uiState.collectAsState()
    val context = LocalContext.current
    val profileUrl = state.profileImageUrl?.trim()
    val notificationVersion by NotificationStore.version.collectAsState()
    val unreadCount = remember(notificationVersion) {
        NotificationStore.unreadCount(context)
    }

    PullToRefreshBox(
        isRefreshing = state.isLoading || registryState.isLoading,
        onRefresh = {
            viewModel.loadDashboard()
            registryViewModel.refresh()
        },
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
                    Text("Field Officer Dashboard", fontSize = 20.sp)
                    Text(
                        text = "Hi, ${state.officerName}",
                        style = MaterialTheme.typography.bodyMedium
                    )
                }

                Row(verticalAlignment = Alignment.CenterVertically) {
                    NotificationActionButton(
                        onClick = { navController.navigate(Routes.NOTIFICATIONS) },
                        unreadCount = unreadCount
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    if (!profileUrl.isNullOrEmpty()) {
                        SubcomposeAsyncImage(
                            model = ImageRequest.Builder(context)
                                .data(profileUrl)
                                .crossfade(true)
                                .build(),
                            contentDescription = "Officer Profile",
                            modifier = Modifier
                                .size(46.dp)
                                .clip(CircleShape)
                                .background(MaterialTheme.colorScheme.surfaceVariant)
                                .clickable { navController.navigate(Routes.PROFILE) },
                            contentScale = ContentScale.Crop,
                            loading = {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(18.dp),
                                    strokeWidth = 2.dp
                                )
                            },
                            error = {
                                Icon(
                                    imageVector = Icons.Default.AccountCircle,
                                    contentDescription = "Default Profile",
                                    modifier = Modifier
                                        .size(46.dp)
                                        .clickable { navController.navigate(Routes.PROFILE) }
                                )
                            }
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

            Button(onClick = { navController.navigate(Routes.FIELD_SITE_VISITS) }, modifier = Modifier.fillMaxWidth()) {
                Text("My Assigned Site Visits")
            }

            Spacer(modifier = Modifier.height(16.dp))

            state.activeCase?.let {
                ActiveCaseCard(
                    case = it,
                    onRelease = { viewModel.releaseCase() },
                    onClick = { navController.navigate(Routes.FIELD_ACTIVE_DETAIL) }
                )
            } ?: Text("No Active Case")

            Spacer(modifier = Modifier.height(16.dp))

            Text("Upcoming Registry Visit", style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(8.dp))
            when {
                registryState.isLoading -> CircularProgressIndicator()
                registryState.error != null -> Text(registryState.error ?: "Failed to load registry")
                registryState.items.isNotEmpty() -> {
                    registryState.items.forEach { item ->
                        RegistryUpcomingCard(
                            assignment = item,
                            onClick = { navController.navigate(Routes.registryDetail(item.id)) }
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                    }
                }
                else -> Text("No upcoming registry visit")
            }

            Spacer(modifier = Modifier.height(16.dp))

            StatCard("Available Cases", state.availableCount.toString())
            StatCard("Completed Visits", state.completedCount.toString())

            Spacer(modifier = Modifier.height(20.dp))

            Button(
                onClick = { navController.navigate(Routes.FIELD_AVAILABLE) },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("View Available Cases")
            }
        }
    }
}


