package com.example.myapplication.ui.feature.home_pase.components

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Map
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.outlined.Explore
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import com.example.myapplication.ui.feature.isDarkAppTheme

private val BrandBlue = Color(0xFF1769D2)
private val SelectedIconSurface = Color(0xFFE7F1FF)
private val MutedNavigation = Color(0xFF8792A2)

@Composable
fun HomeBottomBar(
    selectedItem: String,
    onSelect: (String) -> Unit,
    navController: NavController
) {
    fun navigateSingleTop(route: String) {
        navController.navigate(route) {
            launchSingleTop = true
            restoreState = true
            popUpTo(navController.graph.startDestinationId) {
                saveState = true
            }
        }
    }

    val items = listOf(
        NavigationItem("Home", "home", Icons.Default.Home),
        NavigationItem("Explore", "explore", Icons.Outlined.Explore),
        NavigationItem("Map", "map", Icons.Default.Map),
        NavigationItem("Settings", "settings", Icons.Default.Settings)
    )

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .navigationBarsPadding()
            .padding(horizontal = 18.dp, vertical = 10.dp)
    ) {
        Surface(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(26.dp),
            color = MaterialTheme.colorScheme.surface,
            tonalElevation = 2.dp,
            shadowElevation = 8.dp
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(72.dp)
                    .padding(horizontal = 6.dp, vertical = 4.dp),
                horizontalArrangement = Arrangement.SpaceEvenly,
                verticalAlignment = Alignment.CenterVertically
            ) {
                items.forEach { item ->
                    val selected = selectedItem == item.label
                    val iconColor by animateColorAsState(
                        targetValue = if (isDarkAppTheme()) {
                            if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
                        } else if (selected) BrandBlue else MutedNavigation,
                        label = "${item.label} icon color"
                    )
                    val labelColor by animateColorAsState(
                        targetValue = if (isDarkAppTheme()) {
                            if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
                        } else if (selected) BrandBlue else MutedNavigation,
                        label = "${item.label} label color"
                    )
                    val iconBackground by animateColorAsState(
                        targetValue = if (selected) {
                            if (isDarkAppTheme()) MaterialTheme.colorScheme.surfaceVariant else SelectedIconSurface
                        } else Color.Transparent,
                        label = "${item.label} icon background"
                    )
                    val interactionSource = remember { MutableInteractionSource() }

                    Column(
                        modifier = Modifier
                            .weight(1f)
                            .height(64.dp)
                            .clip(RoundedCornerShape(18.dp))
                            .clickable(
                                interactionSource = interactionSource,
                                indication = null
                            ) {
                                onSelect(item.label)
                                navigateSingleTop(item.route)
                            },
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.Center
                    ) {
                        Box(
                            modifier = Modifier
                                .size(38.dp)
                                .clip(CircleShape)
                                .background(iconBackground),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = item.icon,
                                contentDescription = item.label,
                                tint = iconColor,
                                modifier = Modifier.size(21.dp)
                            )
                        }
                        Text(
                            text = item.label,
                            color = labelColor,
                            fontSize = 11.sp,
                            lineHeight = 14.sp,
                            maxLines = 1
                        )
                    }
                }
            }
        }
    }
}

private data class NavigationItem(
    val label: String,
    val route: String,
    val icon: ImageVector
)
