package com.example.mybroker_admin.feature.admin.listings.presentation.components

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth

import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.mybroker_admin.feature.admin.listings.model.AdminListing


@Composable
fun AssignedListingCard(
    listing: AdminListing,
    onForceRelease: (Int) -> Unit = {}
) {

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 6.dp),
        elevation = CardDefaults.cardElevation(6.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {

            Text("Listing ID: ${listing.id}",
                style = MaterialTheme.typography.labelMedium)

            Spacer(modifier = Modifier.height(4.dp))

            Text("Seller: ${listing.sellerName}")
            Text("Mobile: ${listing.sellerMobile}")
            Text("Location: ${listing.locationText}")

            Spacer(modifier = Modifier.height(6.dp))

            LockStatusBadge(status = listing.status)

            Spacer(modifier = Modifier.height(8.dp))

            if (listing.status == "LOCKED") {
                Text("Handled By: ${listing.assignedOfficer}")
                Text("Officer Mobile: ${listing.officerMobile}")
                Text("Locked: ${listing.lockTime}")

                Spacer(modifier = Modifier.height(8.dp))

                Button(onClick = { onForceRelease(listing.id) }) {
                    Text("Force Release")
                }

            } else {
                Text("No Officer Locked Yet")
            }
        }
    }
}