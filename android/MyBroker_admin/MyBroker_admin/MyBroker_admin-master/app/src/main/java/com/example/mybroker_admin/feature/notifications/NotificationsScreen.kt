package com.example.mybroker_admin.feature.notifications

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.example.mybroker_admin.notification.NotificationItem
import com.example.mybroker_admin.notification.NotificationStore
import com.example.mybroker_admin.notification.NotificationSync
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NotificationsScreen(
    onBack: () -> Unit,
    onNotificationClick: (NotificationItem) -> Unit
) {
    val context = LocalContext.current
    var items by remember { mutableStateOf<List<NotificationItem>>(emptyList()) }
    val version by NotificationStore.version.collectAsState()
    var showUnreadOnly by remember { mutableStateOf(true) }

    LaunchedEffect(version, showUnreadOnly) {
        items = if (showUnreadOnly) {
            NotificationStore.loadUnread(context)
        } else {
            NotificationStore.loadAll(context)
        }
    }

    LaunchedEffect(Unit) {
        NotificationSync.refreshFromServer(context)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Notifications") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(imageVector = Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    if (items.isNotEmpty() && showUnreadOnly) {
                        TextButton(onClick = { NotificationStore.markAllRead(context) }) {
                            Text("Mark all read")
                        }
                    } else if (items.isNotEmpty() && !showUnreadOnly) {
                        TextButton(onClick = { NotificationStore.clear(context) }) {
                            Text("Clear all")
                        }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors()
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 12.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                FilterChip(
                    selected = showUnreadOnly,
                    onClick = { showUnreadOnly = true },
                    label = { Text("Unread") }
                )
                FilterChip(
                    selected = !showUnreadOnly,
                    onClick = { showUnreadOnly = false },
                    label = { Text("All") }
                )
            }
        if (items.isEmpty()) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(16.dp),
                verticalArrangement = Arrangement.Center
            ) {
                Text(
                    text = if (showUnreadOnly) "No unread notifications" else "No notifications yet",
                    style = MaterialTheme.typography.bodyLarge
                )
            }
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 16.dp),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                items(items) { item ->
                    val contentAlpha = if (item.isRead) 0.6f else 1f
                    Card(
                        modifier = Modifier.clickable {
                            NotificationStore.markRead(context, item)
                            onNotificationClick(item)
                        }
                    ) {
                        Column(
                            modifier = Modifier
                                .padding(16.dp)
                                .alpha(contentAlpha)
                        ) {
                            Text(
                                text = item.title,
                                style = MaterialTheme.typography.titleMedium
                            )
                            Text(
                                text = item.body,
                                style = MaterialTheme.typography.bodyMedium,
                                modifier = Modifier.padding(top = 4.dp)
                            )
                            Text(
                                text = formatTimestamp(item.timestamp),
                                style = MaterialTheme.typography.labelSmall,
                                modifier = Modifier.padding(top = 8.dp)
                            )
                        }
                    }
                }
            }
        }
        }
    }
}

private fun formatTimestamp(value: Long): String {
    val formatter = SimpleDateFormat("dd MMM, hh:mm a", Locale.getDefault())
    return formatter.format(Date(value))
}
