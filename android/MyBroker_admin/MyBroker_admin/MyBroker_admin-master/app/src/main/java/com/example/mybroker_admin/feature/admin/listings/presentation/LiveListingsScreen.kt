package com.example.mybroker_admin.feature.admin.listings.presentation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.mybroker_admin.feature.admin.listings.AdminListingsViewModel
import com.example.mybroker_admin.feature.admin.listings.model.AdminListing
import com.example.mybroker_admin.feature.admin.listings.presentation.components.AdminListingCard

@Composable
fun LiveListingsRoute(
    onListingClick: (Int) -> Unit,
    onBack: () -> Unit,
    vm: AdminListingsViewModel = viewModel()
) {
    val listings by vm.listings.collectAsStateWithLifecycle()
    val isLoading by vm.isLoading.collectAsStateWithLifecycle()
    val errorMessage by vm.errorMessage.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) {
        vm.loadListingsByStatus(status = "live")
    }

    LiveListingsScreen(
        listings = listings,
        isLoading = isLoading,
        errorMessage = errorMessage,
        onListingClick = onListingClick,
        onBack = onBack
    )
}

@Composable
fun LiveListingsScreen(
    listings: List<AdminListing>,
    isLoading: Boolean,
    errorMessage: String?,
    onListingClick: (Int) -> Unit,
    onBack: () -> Unit
) {
    var stateFilter by remember { mutableStateOf("") }
    var districtFilter by remember { mutableStateOf("") }
    var appliedState by remember { mutableStateOf("") }
    var appliedDistrict by remember { mutableStateOf("") }

    val filteredListings = remember(listings, appliedState, appliedDistrict) {
        listings.filter { item ->
            val location = item.locationText.lowercase()
            val stateOk = appliedState.isBlank() || location.contains(appliedState.trim().lowercase())
            val districtOk = appliedDistrict.isBlank() || location.contains(appliedDistrict.trim().lowercase())
            stateOk && districtOk
        }
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = "Live Listings",
                    style = MaterialTheme.typography.headlineSmall
                )
                TextButton(onClick = onBack) { Text("Back") }
            }
        }

        item {
            OutlinedTextField(
                value = stateFilter,
                onValueChange = { stateFilter = it },
                label = { Text("Filter by State") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )
        }

        item {
            OutlinedTextField(
                value = districtFilter,
                onValueChange = { districtFilter = it },
                label = { Text("Filter by District") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )
        }

        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = {
                        appliedState = stateFilter
                        appliedDistrict = districtFilter
                    },
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Apply Filter")
                }

                TextButton(
                    onClick = {
                        stateFilter = ""
                        districtFilter = ""
                        appliedState = ""
                        appliedDistrict = ""
                    },
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Clear")
                }
            }
        }

        if (isLoading) {
            item { CircularProgressIndicator() }
            return@LazyColumn
        }

        if (!errorMessage.isNullOrBlank()) {
            item { Text(text = errorMessage, color = MaterialTheme.colorScheme.error) }
            return@LazyColumn
        }

        if (filteredListings.isEmpty()) {
            item { Text("No live listings found.") }
            return@LazyColumn
        }

        items(filteredListings, key = { it.id }) { listing ->
            AdminListingCard(
                listingId = listing.id,
                sellerName = listing.sellerName,
                price = listing.priceText,
                location = listing.locationText,
                onClick = { onListingClick(listing.id) }
            )
        }
    }
}
