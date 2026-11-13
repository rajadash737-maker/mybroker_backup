package com.example.mybroker_admin.feature.superadmin.listings.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.mybroker_admin.feature.superadmin.listings.model.SuperAdminListingItem

@Composable
fun SuperAdminListingCard(
    item: SuperAdminListingItem,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() },
        elevation = CardDefaults.cardElevation(6.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("Listing ID: ${item.id}")
            Spacer(Modifier.height(4.dp))
            Text("Seller: ${item.sellerName}")
            Text("Mobile: ${item.sellerMobile}")
            Spacer(Modifier.height(6.dp))
            Text(
                text = "Status: ${item.status}",
                color = MaterialTheme.colorScheme.primary
            )
        }
    }
}
