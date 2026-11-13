package com.example.myapplication.ui.feature.buyer.visit_request

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.clickable
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import java.text.NumberFormat
import java.util.Locale

@Composable
fun BuyerLandDetailsScreen(
    landId: Int,
    viewModel: BuyerLandDetailsViewModel,
    onBack: () -> Unit,
    dealAmount: Double?,
    bookingStatus: String,
    registryDate: String,
    registryTime: String,
    registryLocation: String
) {
    val state by viewModel.uiState.collectAsState()
    LaunchedEffect(landId) { viewModel.load(landId) }
    Column(Modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Back", Modifier.clickable(onClick = onBack).padding(bottom = 8.dp), color = MaterialTheme.colorScheme.primary)
        when {
            state.loading -> CircularProgressIndicator()
            state.error != null -> Text(state.error.orEmpty(), color = MaterialTheme.colorScheme.error)
            state.land != null -> {
                val land = state.land!!
                Text(land.title, style = MaterialTheme.typography.headlineSmall)
                Text("Listing #${land.id} • ${land.location}")
                Text("Price: ${NumberFormat.getCurrencyInstance(Locale("en", "IN")).format(dealAmount ?: land.dealAmount ?: land.expectedPrice)}")
                Text("Status: ${bookingStatus.ifBlank { land.bookingStatus.orEmpty() }}")
                Text("Area: ${land.area} ${land.areaUnit}")
                Text("Registry date: ${registryDate.ifBlank { land.registryDate.orEmpty() }}")
                Text("Registry time: ${registryTime.ifBlank { land.registryTime.orEmpty() }}")
                Text("Registry location: ${registryLocation.ifBlank { land.registryLocation.orEmpty() }}")
            }
            else -> Text("Land details unavailable")
        }
    }
}
