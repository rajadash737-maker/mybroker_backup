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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
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
import com.example.mybroker_admin.feature.admin.listings.RegistryPendingState
import com.example.mybroker_admin.feature.admin.listings.RegistryPendingUi
import com.example.mybroker_admin.feature.admin.listings.RegistryPendingViewModel

@Composable
fun RegistryPendingRoute(
    onListingClick: (Int) -> Unit,
    onBack: () -> Unit
) {
    val vm: RegistryPendingViewModel = viewModel()
    val state = vm.state.collectAsState().value

    LaunchedEffect(Unit) {
        if (!state.loaded) vm.load()
    }

    RegistryPendingScreen(
        state = state,
        onRetry = vm::load,
        onListingClick = onListingClick,
        onBack = onBack
    )
}

@Composable
fun RegistryPendingScreen(
    state: RegistryPendingState,
    onRetry: () -> Unit,
    onListingClick: (Int) -> Unit,
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
                text = "Pending Registry Verification",
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
                    text = "No pending registry verifications",
                    style = MaterialTheme.typography.bodyMedium
                )
            }
            else -> {
                LazyColumn(
                    contentPadding = PaddingValues(vertical = 8.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(state.items, key = { it.bookingId }) { item ->
                        RegistryPendingCard(item = item, onClick = { onListingClick(item.listingId) })
                    }
                }
            }
        }
    }
}

@Composable
private fun RegistryPendingCard(
    item: RegistryPendingUi,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() },
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Text(text = "Listing ID: ${item.listingId}", style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(6.dp))
            Text(text = "Seller: ${item.sellerName ?: "-"} - ${item.sellerMobile ?: "-"}")
            Text(text = "Buyer: ${item.buyerName} - ${item.buyerMobile}")
            Text(text = "Registry Date: ${item.registryDate ?: "-"}")
            Text(text = "Registry Time: ${item.registryTime ?: "-"}")
            Text(text = "Location: ${item.registryLocation ?: "-"}")
        }
    }
}
