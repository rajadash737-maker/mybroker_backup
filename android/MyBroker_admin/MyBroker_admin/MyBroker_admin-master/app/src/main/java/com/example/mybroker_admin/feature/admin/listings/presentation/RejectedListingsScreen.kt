package com.example.mybroker_admin.feature.admin.listings.presentation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.mybroker_admin.feature.admin.listings.AdminListingsViewModel
import com.example.mybroker_admin.feature.admin.listings.model.AdminListing
import com.example.mybroker_admin.feature.admin.listings.presentation.components.RejectedListingCard
import com.example.mybroker_admin.feature.admin.listings.presentation.components.SectionCard

@Composable
fun RejectedListingsRoute(
    onListingClick: (Int) -> Unit,
    onBack: () -> Unit,
    vm: AdminListingsViewModel = viewModel()
) {
    val listings by vm.listings.collectAsStateWithLifecycle()
    val isLoading by vm.isLoading.collectAsStateWithLifecycle()
    val errorMessage by vm.errorMessage.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) {
        vm.loadRejectedListings()
    }

    RejectedListingsScreen(
        listings = listings,
        isLoading = isLoading,
        errorMessage = errorMessage,
        onApplyFilter = { state, district -> vm.loadRejectedListings(state, district) },
        onClearFilter = { vm.loadRejectedListings() },
        onListingClick = onListingClick,
        onBack = onBack
    )
}

@Composable
fun RejectedListingsScreen(
    listings: List<AdminListing>,
    isLoading: Boolean,
    errorMessage: String?,
    onApplyFilter: (String, String) -> Unit,
    onClearFilter: () -> Unit,
    onListingClick: (Int) -> Unit,
    onBack: () -> Unit
) {
    var stateFilter by remember { mutableStateOf("") }
    var districtFilter by remember { mutableStateOf("") }

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
                text = "Rejected Listings",
                style = MaterialTheme.typography.headlineMedium
            )
            TextButton(onClick = onBack) { Text("Back") }
        }

        Spacer(modifier = Modifier.height(12.dp))

        SectionCard(title = "Filters") {
            OutlinedTextField(
                value = stateFilter,
                onValueChange = { stateFilter = it },
                label = { Text("State") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )

            Spacer(modifier = Modifier.height(8.dp))

            OutlinedTextField(
                value = districtFilter,
                onValueChange = { districtFilter = it },
                label = { Text("District") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )

            Spacer(modifier = Modifier.height(10.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = { onApplyFilter(stateFilter.trim(), districtFilter.trim()) },
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Apply")
                }
                OutlinedButton(
                    onClick = {
                        stateFilter = ""
                        districtFilter = ""
                        onClearFilter()
                    },
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Clear")
                }
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        Text(
            text = "Total Rejected: ${listings.size}",
            style = MaterialTheme.typography.titleMedium
        )

        Spacer(modifier = Modifier.height(8.dp))

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f, fill = true)
        ) {
            when {
                isLoading -> {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.Center
                    ) {
                        CircularProgressIndicator()
                    }
                }
                !errorMessage.isNullOrBlank() -> {
                    Text(
                        text = errorMessage,
                        color = MaterialTheme.colorScheme.error
                    )
                }
                listings.isEmpty() -> {
                    Text("No rejected listings found.")
                }
                else -> {
                    LazyColumn(
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        items(listings, key = { it.id }) { listing ->
                            RejectedListingCard(
                                listingId = listing.id,
                                listingCode = listing.listingCode,
                                sellerName = listing.sellerName,
                                sellerMobile = listing.sellerMobile,
                                price = listing.priceText,
                                location = listing.locationText,
                                onClick = { onListingClick(listing.id) }
                            )
                        }
                    }
                }
            }
        }
    }
}
