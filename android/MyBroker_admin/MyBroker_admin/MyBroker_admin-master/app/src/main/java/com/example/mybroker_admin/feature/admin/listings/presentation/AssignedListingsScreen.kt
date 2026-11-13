package com.example.mybroker_admin.feature.admin.listings.presentation


import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.mybroker_admin.feature.admin.listings.AdminListingsViewModel
import com.example.mybroker_admin.feature.admin.listings.model.AdminListing
import com.example.mybroker_admin.feature.admin.listings.presentation.components.AssignedListingCard
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.layout.Arrangement



@Composable
fun AssignedListingsRoute(
    vm: AdminListingsViewModel = viewModel()
) {
    val listings by vm.listings.collectAsStateWithLifecycle()
    val isLoading by vm.isLoading.collectAsStateWithLifecycle()
    val errorMessage by vm.errorMessage.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) {
        vm.loadAssignmentBoard()   // IMPORTANT
    }

    val lockedCases = listings.filter { it.status.equals("LOCKED", true) }
    val availableCases = listings.filter { it.status.equals("AVAILABLE", true) }

    AssignedListingsScreen(
        lockedCases = lockedCases,
        availableCases = availableCases,
        isLoading = isLoading,
        errorMessage = errorMessage,
        onForceRelease = { id -> vm.forceReleaseCase(id) }
    )
}

@Composable
fun AssignedListingsScreen(
    lockedCases: List<AdminListing>,
    availableCases: List<AdminListing>,
    isLoading: Boolean,
    errorMessage: String?,
    onForceRelease: (Int) -> Unit
) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text("Assigned To Field Officer", style = MaterialTheme.typography.titleLarge)
        }

        when {
            isLoading -> {
                item { CircularProgressIndicator() }
            }

            !errorMessage.isNullOrBlank() -> {
                item { Text(errorMessage, color = MaterialTheme.colorScheme.error) }
            }

            else -> {
                item { SectionTitle("Locked Cases (${lockedCases.size})") }

                items(lockedCases, key = { it.id }) { listing ->
                    AssignedListingCard(listing = listing, onForceRelease = onForceRelease)
                }

                item { SectionTitle("Available Cases (${availableCases.size})") }

                items(availableCases, key = { it.id }) { listing ->
                    AssignedListingCard(listing = listing, onForceRelease = onForceRelease)
                }

                if (lockedCases.isEmpty() && availableCases.isEmpty()) {
                    item { Text("No cases found.") }
                }
            }
        }
    }
}


@Composable
fun SectionTitle(title: String) {
    Text(
        text = title,
        style = MaterialTheme.typography.titleMedium,
        modifier = Modifier.padding(vertical = 8.dp)
    )
}
