package com.example.mybroker_admin.feature.superadmin.listings.screen

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import com.example.mybroker_admin.core.navigation.Routes
import com.example.mybroker_admin.feature.superadmin.listings.components.SuperAdminListingCard
import com.example.mybroker_admin.feature.superadmin.listings.model.SuperAdminListingFilters
import com.example.mybroker_admin.feature.superadmin.listings.viewmodel.SuperAdminListingsViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SuperAdminListingsScreen(navController: NavHostController) {
    val vm: SuperAdminListingsViewModel = viewModel()
    val state by vm.state.collectAsState()

    val statusChips = SuperAdminListingFilters.statusOptions

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("All Listings") },
                navigationIcon = {
                    androidx.compose.material3.TextButton(onClick = { navController.popBackStack() }) {
                        Text("Back")
                    }
                }
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .padding(padding)
                .padding(16.dp)
        ) {
            item {
                OutlinedTextField(
                    value = state.searchQuery,
                    onValueChange = vm::onSearchQueryChange,
                    label = { Text("Search by seller, listing id, city, etc.") },
                    modifier = Modifier.fillMaxWidth()
                )
            }

            item { Spacer(modifier = Modifier.height(8.dp)) }

            item {
                Button(
                    onClick = vm::applySearch,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Apply Search")
                }
            }

            item { Spacer(modifier = Modifier.height(12.dp)) }

            item {
                Row(
                    modifier = Modifier.horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    statusChips.forEach { (label, value) ->
                        FilterChip(
                            selected = state.statusFilter == value,
                            onClick = { vm.onStatusSelected(value) },
                            label = { Text(label) }
                        )
                    }
                }
            }

            item { Spacer(modifier = Modifier.height(16.dp)) }

            if (state.isLoading) {
                item {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
                        CircularProgressIndicator()
                    }
                }
            } else if (!state.error.isNullOrBlank()) {
                item {
                    Text(state.error ?: "Failed to load listings", color = MaterialTheme.colorScheme.error)
                }
            } else if (state.listings.isEmpty()) {
                val hasQuery = state.searchQuery.isNotBlank() || state.statusFilter != null
                item {
                    Text(
                        when {
                            state.statusFilter == "draft" -> "No draft listings found"
                            hasQuery -> "Not found"
                            else -> "No listings found."
                        }
                    )
                }
            } else {
                items(state.listings.size) { idx ->
                    val item = state.listings[idx]
                    SuperAdminListingCard(
                        item = item,
                        onClick = { navController.navigate(Routes.superAdminListingDetail(item.id)) }
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                }

                if (state.isLoadingMore) {
                    item {
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
                            CircularProgressIndicator()
                        }
                    }
                } else if (state.canLoadMore) {
                    item {
                        Button(
                            onClick = vm::loadMore,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Load More")
                        }
                    }
                }
            }
        }
    }
}
