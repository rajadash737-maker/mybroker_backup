package com.example.mybroker_admin.core.components

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.example.mybroker_admin.domain.model.RegistryStatus

@Composable
fun RegistryStatusChip(
    status: RegistryStatus,
    modifier: Modifier = Modifier
) {
    val (background, content) = statusColors(status)

    Surface(
        color = background,
        contentColor = content,
        shape = MaterialTheme.shapes.small,
        modifier = modifier
    ) {
        Text(
            text = status.displayName,
            style = MaterialTheme.typography.labelMedium,
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
        )
    }
}

private fun statusColors(status: RegistryStatus): Pair<Color, Color> {
    return when (status) {
        RegistryStatus.BOOKED -> Color(0xFFE8EAF6) to Color(0xFF1A237E)
        RegistryStatus.SCHEDULED -> Color(0xFFE3F2FD) to Color(0xFF0D47A1)
        RegistryStatus.IN_PROGRESS -> Color(0xFFFFF3E0) to Color(0xFFE65100)
        RegistryStatus.COMPLETED -> Color(0xFFE8F5E9) to Color(0xFF1B5E20)
    }
}
