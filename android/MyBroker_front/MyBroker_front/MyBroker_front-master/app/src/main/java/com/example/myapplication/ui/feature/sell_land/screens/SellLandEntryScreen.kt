package com.example.myapplication.ui.feature.sell_land.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.myapplication.ui.feature.sell_land.model.SellLandResponse
import com.example.myapplication.ui.feature.sell_land.viewmodel.SellLandEntryState
import com.example.myapplication.ui.feature.sell_land.viewmodel.SellLandViewModel

@Composable
fun SellLandEntryScreen(
    viewModel: SellLandViewModel,
    onResume: (SellLandResponse) -> Unit,
    onCreateNew: (List<SellLandResponse>) -> Unit
) {
    val state by viewModel.entryState.collectAsState()
    Scaffold { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text("Sell Land", style = MaterialTheme.typography.headlineSmall)
            when (val current = state) {
                SellLandEntryState.Idle, SellLandEntryState.LoadingListings,
                is SellLandEntryState.LoadingDraft -> {
                    CircularProgressIndicator()
                    Text(if (current is SellLandEntryState.LoadingDraft) "Loading your saved listing…" else "Checking your saved drafts…")
                }
                is SellLandEntryState.ChooseDraft -> {
                    if (current.listings.size > 1) {
                        Text("Choose a draft to resume")
                        LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                            items(current.listings, key = { it.id }) { listing ->
                                DraftChoice(listing = listing, onResume = { onResume(listing) })
                            }
                        }
                        OutlinedButton(onClick = { onCreateNew(current.listings) }, modifier = Modifier.fillMaxWidth()) {
                            Text("Create New Listing")
                        }
                    }
                }
                is SellLandEntryState.Failed -> {
                    Text(current.message, color = MaterialTheme.colorScheme.error)
                    Button(
                        onClick = { current.listingId?.let(viewModel::resumeDraft) ?: viewModel.findDraftsForNewEntry() },
                        modifier = Modifier.fillMaxWidth()
                    ) { Text("Retry") }
                }
                is SellLandEntryState.Ready, SellLandEntryState.Fresh -> CircularProgressIndicator()
            }
        }
    }
}

@Composable
private fun DraftChoice(listing: SellLandResponse, onResume: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(listing.title?.takeIf { it.isNotBlank() } ?: "Listing ${listing.id}", style = MaterialTheme.typography.titleMedium)
            Text("ID: ${listing.id} · Status: ${listing.status}")
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                Button(onClick = onResume) { Text("Resume") }
            }
        }
    }
}
