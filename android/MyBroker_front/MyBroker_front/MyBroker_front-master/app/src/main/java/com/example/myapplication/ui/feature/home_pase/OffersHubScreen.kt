package com.example.myapplication.ui.feature.home_pase

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun OffersHubScreen(
    onBuyerOffers: () -> Unit,
    onSellerOffers: () -> Unit
) {
    Column(
        modifier = Modifier.fillMaxSize().padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text("Offers", style = MaterialTheme.typography.headlineSmall)
        Text("Choose the offers you want to review.")
        Button(onClick = onBuyerOffers, modifier = Modifier.fillMaxWidth()) {
            Text("Seller counter-offers")
        }
        Button(onClick = onSellerOffers, modifier = Modifier.fillMaxWidth()) {
            Text("Offers on my listings")
        }
    }
}
