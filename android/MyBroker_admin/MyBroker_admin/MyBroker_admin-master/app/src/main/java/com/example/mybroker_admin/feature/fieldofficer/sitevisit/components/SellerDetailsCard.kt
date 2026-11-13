package com.example.mybroker_admin.feature.fieldofficer.sitevisit.components

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun SellerDetailsCard(
    name: String,
    mobile: String,
    sellerType: String,
    category: String
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = 12.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {

            Text("Seller Details", style = MaterialTheme.typography.titleMedium)

            Spacer(modifier = Modifier.height(8.dp))

            Column {
                Text("Name: $name")
                Text("Mobile: $mobile")
                Text("Category: $category")
                Text("Seller Type: $sellerType")
            }
        }
    }
}
