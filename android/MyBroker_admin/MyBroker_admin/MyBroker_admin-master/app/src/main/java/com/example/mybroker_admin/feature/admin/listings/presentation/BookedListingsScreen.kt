package com.example.mybroker_admin.feature.admin.listings.presentation

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Divider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.mybroker_admin.feature.admin.listings.BookedListingUi
import com.example.mybroker_admin.feature.admin.listings.BookedListingsState
import com.example.mybroker_admin.feature.admin.listings.BookedListingsViewModel

@Composable
fun BookedListingsRoute(
    onListingClick: (Int) -> Unit = {},
    onBack: () -> Unit = {}
) {
    val vm: BookedListingsViewModel = viewModel()
    val state = vm.state.collectAsState().value

    LaunchedEffect(Unit) {
        if (!state.loaded) vm.load()
    }

    BookedListingsScreen(
        state = state,
        onRetry = vm::load,
        onListingClick = onListingClick,
        onBack = onBack
    )
}

@Composable
fun BookedListingsScreen(
    state: BookedListingsState,
    onRetry: () -> Unit,
    onListingClick: (Int) -> Unit,
    onBack: () -> Unit,
    title: String = "Booked Listings"
) {
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
            Text(
                text = title,
                style = MaterialTheme.typography.headlineMedium
            )
            TextButton(onClick = onBack) { Text("Back") }
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
                OutlinedButton(onClick = onRetry) {
                    Text("Retry")
                }
            }
            state.items.isEmpty() -> {
                Text(
                    text = "No booked listings",
                    style = MaterialTheme.typography.bodyMedium
                )
            }
            else -> {
                LazyColumn(
                    contentPadding = PaddingValues(vertical = 8.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(state.items, key = { it.id }) { item ->
                        BookedListingCard(
                            item = item,
                            onClick = { onListingClick(item.id) }
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun BookedListingCard(
    item: BookedListingUi,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() },
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
                        text = "Listing ID: ${item.id}",
                        style = MaterialTheme.typography.titleMedium
                    )
                }
                StatusPill(
                    text = item.bookingStatus ?: "BOOKED",
                    colors = bookingStatusColors(item.bookingStatus)
                )
            }
            Spacer(modifier = Modifier.height(10.dp))

            InfoRow(label = "Seller", value = "${item.sellerName} - ${item.sellerMobile ?: "-"}")
            InfoRow(label = "Buyer", value = "${item.buyerName ?: "-"} - ${item.buyerMobile ?: "-"}")
            InfoRow(
                label = "Field Officer",
                value = listOfNotNull(item.fieldOfficerName, item.fieldOfficerMobile)
                    .joinToString(" - ")
                    .ifBlank { "-" }
            )

            Spacer(modifier = Modifier.height(6.dp))
            Divider(color = MaterialTheme.colorScheme.surfaceVariant)
            Spacer(modifier = Modifier.height(6.dp))

            InfoRow(label = "Expected Price", value = item.expectedPrice ?: "-")
            InfoRow(label = "Deal Price", value = item.dealPrice ?: "-")
            InfoRow(label = "Booking Fee", value = item.bookingFee ?: "-")
            InfoRow(label = "Payment", value = item.paymentStatus ?: "-")
            InfoRow(label = "Booked At", value = item.bookedAt ?: "-")
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
        modifier = modifier.widthIn(min = 64.dp)
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.labelMedium,
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
        )
    }
}

private fun bookingStatusColors(status: String?): Pair<Color, Color> {
    return when (status?.uppercase()) {
        "BOOKED" -> Color(0xFFE3F2FD) to Color(0xFF0D47A1)
        "REGISTRY SCHEDULED" -> Color(0xFFFFF3E0) to Color(0xFFE65100)
        "IN PROCESS" -> Color(0xFFFFF8E1) to Color(0xFFF57F17)
        "REGISTRY DONE" -> Color(0xFFE8F5E9) to Color(0xFF1B5E20)
        "SOLD" -> Color(0xFFE0F7FA) to Color(0xFF006064)
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
