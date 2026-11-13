package com.example.mybroker_admin.feature.admin.listings.presentation.components


import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp


@Composable
fun AdminListingCard(
    listingId: Int,
    sellerName: String,
    price: String,
    location: String,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() },
        elevation = CardDefaults.cardElevation(6.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {

            Text("Listing ID: LST-$listingId")
            Spacer(Modifier.height(4.dp))

            Text("Seller: $sellerName")
            Text("Location: $location")
            Text("Price: $price")

            Spacer(Modifier.height(8.dp))

            Text(
                text = "Status: Pending",
                color = MaterialTheme.colorScheme.primary
            )
        }
    }
}
