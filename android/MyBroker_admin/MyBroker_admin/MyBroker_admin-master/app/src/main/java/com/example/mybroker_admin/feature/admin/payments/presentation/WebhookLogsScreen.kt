package com.example.mybroker_admin.feature.admin.payments.presentation

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Divider
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.mybroker_admin.feature.admin.payments.WebhookLogUi
import com.example.mybroker_admin.feature.admin.payments.WebhookLogsState
import com.example.mybroker_admin.feature.admin.payments.WebhookLogsViewModel

@Composable
fun WebhookLogsRoute(
    onBack: () -> Unit = {}
) {
    val vm: WebhookLogsViewModel = viewModel()
    val state = vm.state.collectAsState().value

    LaunchedEffect(Unit) {
        if (!state.loaded) vm.load()
    }

    WebhookLogsScreen(
        state = state,
        onRetry = vm::load,
        onContextFilter = vm::updateContextFilter,
        onStatusFilter = vm::updateStatusFilter,
        onBack = onBack
    )
}

@Composable
fun WebhookLogsScreen(
    state: WebhookLogsState,
    onRetry: () -> Unit,
    onContextFilter: (String?) -> Unit,
    onStatusFilter: (String?) -> Unit,
    onBack: () -> Unit
) {
    val contextOptions = listOf(
        "All" to null,
        "Buyer" to "buyer",
        "Seller" to "seller",
        "Unknown" to "unknown"
    )
    val statusOptions = listOf(
        "All" to null,
        "Processed" to "processed",
        "Failed" to "failed",
        "Ignored" to "ignored",
        "Duplicate" to "duplicate",
        "Success" to "success"
    )

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = "Webhook Logs",
                    style = MaterialTheme.typography.headlineMedium
                )
                Text(
                    text = "Total: ${state.total}",
                    style = MaterialTheme.typography.bodyMedium
                )
            }
            TextButton(onClick = onBack) { Text("Back") }
        }

        Spacer(modifier = Modifier.height(8.dp))

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            contextOptions.forEach { (label, value) ->
                FilterChip(
                    selected = state.selectedContext == value,
                    onClick = { onContextFilter(value) },
                    label = { Text(label) }
                )
            }
        }

        Spacer(modifier = Modifier.height(6.dp))

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            statusOptions.forEach { (label, value) ->
                FilterChip(
                    selected = state.selectedStatus == value,
                    onClick = { onStatusFilter(value) },
                    label = { Text(label) }
                )
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        when {
            state.isLoading -> {
                Spacer(modifier = Modifier.height(24.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.Center
                ) {
                    CircularProgressIndicator()
                }
            }
            state.error != null -> {
                Text(
                    text = state.error,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.error
                )
                Spacer(modifier = Modifier.height(12.dp))
                OutlinedButton(onClick = onRetry) { Text("Retry") }
            }
            state.items.isEmpty() -> {
                Text(
                    text = "No webhook logs found",
                    style = MaterialTheme.typography.bodyMedium
                )
            }
            else -> {
                LazyColumn(
                    contentPadding = PaddingValues(vertical = 8.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(state.items, key = { it.id }) { item ->
                        WebhookLogCard(item = item)
                    }
                }
            }
        }
    }
}

@Composable
private fun WebhookLogCard(item: WebhookLogUi) {
    var expanded by remember { mutableStateOf(false) }

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = item.event,
                        style = MaterialTheme.typography.titleMedium
                    )
                    Text(
                        text = "Event ID: ${item.eventId ?: "-"}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                StatusPill(
                    text = item.status,
                    colors = statusColors(item.status)
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                StatusPill(
                    text = item.paymentContext,
                    colors = contextColors(item.paymentContext),
                    modifier = Modifier.widthIn(min = 80.dp)
                )
                Text(
                    text = item.createdAt,
                    style = MaterialTheme.typography.bodySmall
                )
            }

            Spacer(modifier = Modifier.height(8.dp))
            Divider(color = MaterialTheme.colorScheme.surfaceVariant)
            Spacer(modifier = Modifier.height(6.dp))

            InfoRow(label = "Order ID", value = item.orderId ?: "-")
            InfoRow(label = "Payment ID", value = item.paymentId ?: "-")

            if (!item.error.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = "Error: ${item.error}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error
                )
            }

            Spacer(modifier = Modifier.height(8.dp))
            TextButton(onClick = { expanded = !expanded }) {
                Text(if (expanded) "Hide Payload" else "Show Payload")
            }
            if (expanded) {
                Surface(
                    color = MaterialTheme.colorScheme.surfaceVariant,
                    shape = MaterialTheme.shapes.small,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        text = item.payload,
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(10.dp)
                    )
                }
            }
        }
    }
}

@Composable
private fun StatusPill(
    text: String,
    colors: Pair<Color, Color>,
    modifier: Modifier = Modifier
) {
    Surface(
        color = colors.first,
        contentColor = colors.second,
        shape = MaterialTheme.shapes.small,
        modifier = modifier.widthIn(min = 70.dp)
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.labelMedium,
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
        )
    }
}

private fun statusColors(status: String): Pair<Color, Color> {
    return when (status.uppercase()) {
        "PROCESSED", "SUCCESS" -> Color(0xFFE8F5E9) to Color(0xFF1B5E20)
        "FAILED" -> Color(0xFFFFEBEE) to Color(0xFFB71C1C)
        "IGNORED" -> Color(0xFFF3E5F5) to Color(0xFF6A1B9A)
        "DUPLICATE" -> Color(0xFFFFF3E0) to Color(0xFFE65100)
        else -> Color(0xFFE3F2FD) to Color(0xFF0D47A1)
    }
}

private fun contextColors(context: String): Pair<Color, Color> {
    return when (context.uppercase()) {
        "BUYER" -> Color(0xFFE0F7FA) to Color(0xFF006064)
        "SELLER" -> Color(0xFFE8F5E9) to Color(0xFF1B5E20)
        else -> Color(0xFFEDE7F6) to Color(0xFF4527A0)
    }
}

@Composable
private fun InfoRow(
    label: String,
    value: String
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(modifier = Modifier.width(12.dp))
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium
        )
    }
}
