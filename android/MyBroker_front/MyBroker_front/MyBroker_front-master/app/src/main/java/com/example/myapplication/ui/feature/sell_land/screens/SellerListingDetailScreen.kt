package com.example.myapplication.ui.feature.sell_land.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.example.myapplication.network.ApiClient
import com.example.myapplication.ui.feature.sell_land.model.SellLandResponse
import com.example.myapplication.ui.feature.sell_land.viewmodel.SellLandViewModel

@Composable
fun SellerListingDetailScreen(listingId: String, viewModel: SellLandViewModel, onBack: () -> Unit) {
    val context = LocalContext.current
    var listing by remember { mutableStateOf<SellLandResponse?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var loading by remember { mutableStateOf(true) }
    LaunchedEffect(listingId) {
        loading = true
        runCatching {
            ApiClient.init(context.applicationContext)
            ApiClient.apiService.getListingDetails(listingId.toInt())
        }.onSuccess { response ->
            if (response.isSuccessful) listing = response.body() else error = "Unable to load listing (${response.code()})"
        }.onFailure { error = it.message ?: "Unable to load listing" }
        loading = false
    }
    Column(Modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Back", Modifier.clickable(onClick = onBack).padding(bottom = 8.dp), color = MaterialTheme.colorScheme.primary)
        when {
            loading -> CircularProgressIndicator()
            error != null -> Text(error.orEmpty(), color = MaterialTheme.colorScheme.error)
            listing != null -> {
                val item = listing!!
                Text(item.title ?: "Land listing", style = MaterialTheme.typography.headlineSmall)
                Text("Listing #${item.id}")
                Text("Status: ${item.status}")
                Text("Expected price: ₹ ${item.expectedPrice ?: 0}")
                Text("Payment: ${item.paymentStatus}")
                item.dealAmount?.let { Text("Deal amount: ₹ $it") }
                item.registryDate?.let { Text("Registry date: $it") }
                item.registryTime?.let { Text("Registry time: $it") }
                item.registryLocation?.let { Text("Registry location: $it") }
            }
        }
    }
}
