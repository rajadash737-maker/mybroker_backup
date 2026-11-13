package com.example.mybroker_admin.feature.admin.listings.presentation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.mybroker_admin.feature.admin.listings.LockedListingUi
import com.example.mybroker_admin.feature.admin.listings.LockedListingsState
import com.example.mybroker_admin.feature.admin.listings.LockedListingsViewModel
import com.example.mybroker_admin.feature.admin.listings.presentation.components.LockStatusBadge

@Composable
fun LockedListingsRoute(
    onBack: () -> Unit = {}
) {
    val vm: LockedListingsViewModel = viewModel()
    val state = vm.state.collectAsState().value

    LaunchedEffect(Unit) {
        if (!state.loaded) vm.load()
    }

    LockedListingsScreen(
        state = state,
        onRetry = vm::load,
        onForceRelease = vm::forceRelease,
        onBack = onBack
    )
}

@Composable
fun LockedListingsScreen(
    state: LockedListingsState,
    onRetry: () -> Unit,
    onForceRelease: (Int) -> Unit,
    onBack: () -> Unit
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
                text = "Locked Listings",
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
                    text = "No locked listings",
                    style = MaterialTheme.typography.bodyMedium
                )
            }
            else -> {
                LazyColumn(
                    contentPadding = PaddingValues(vertical = 8.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(state.items, key = { it.id }) { item ->
                        LockedListingCard(
                            item = item,
                            onForceRelease = { onForceRelease(item.id) }
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun LockedListingCard(
    item: LockedListingUi,
    onForceRelease: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Listing ID: ${item.id}",
                    style = MaterialTheme.typography.titleMedium
                )

                LockStatusBadge(status = "Locked")
            }

            Spacer(modifier = Modifier.height(6.dp))
            Text(text = "Seller: ${item.sellerName} • ${item.sellerMobile ?: "-"}")
            Text(text = "Buyer: ${item.buyerName ?: "-"} • ${item.buyerMobile ?: "-"}")
            Text(text = "Expected Price: ${item.expectedPrice ?: "-"}")
            Text(text = "Deal Price: ${item.dealPrice ?: "-"}")
            Text(text = "Locked For: ${formatLockedDuration(item.lockedForSeconds)}")

            Spacer(modifier = Modifier.height(8.dp))
            FilledTonalButton(
                onClick = onForceRelease,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Force Release")
            }
        }
    }
}

private fun formatLockedDuration(seconds: Int?): String {
    if (seconds == null || seconds <= 0) return "-"
    val minutes = seconds / 60
    val hours = minutes / 60
    val remainingMinutes = minutes % 60
    return if (hours > 0) "${hours}h ${remainingMinutes}m" else "${remainingMinutes}m"
}
