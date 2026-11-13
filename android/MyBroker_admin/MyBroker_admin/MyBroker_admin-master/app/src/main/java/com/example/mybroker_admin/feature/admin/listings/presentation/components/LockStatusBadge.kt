package com.example.mybroker_admin.feature.admin.listings.presentation.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp


@Composable
fun LockStatusBadge(status: String) {

    val color = when (status) {
        "LOCKED" -> Color(0xFF4CAF50)
        "AVAILABLE" -> Color(0xFFFFC107)
        else -> Color.Gray
    }

    Box(
        modifier = Modifier
            .background(color, RoundedCornerShape(50))
            .padding(horizontal = 12.dp, vertical = 4.dp)
    ) {
        Text(
            text = status,
            color = Color.White,
            style = MaterialTheme.typography.labelSmall
        )
    }
}