package com.example.mybroker_admin.feature.common

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Notifications
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier

@Composable
fun NotificationActionButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    hasUnread: Boolean = false,
    unreadCount: Int? = null
) {
    val safeCount = unreadCount?.coerceAtLeast(0)
    val showBadge = (safeCount != null && safeCount > 0) || hasUnread
    val badgeText = when {
        safeCount == null -> null
        safeCount > 99 -> "99+"
        safeCount > 0 -> safeCount.toString()
        else -> null
    }

    IconButton(
        onClick = onClick,
        modifier = modifier
    ) {
        BadgedBox(
            badge = {
                if (showBadge) {
                    Badge {
                        if (badgeText != null) {
                            Text(badgeText)
                        }
                    }
                }
            }
        ) {
            Icon(
                imageVector = Icons.Outlined.Notifications,
                contentDescription = "Notifications"
            )
        }
    }
}
