package com.example.mybroker_admin.feature.admin.cancel.presentation.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
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
import com.example.mybroker_admin.feature.admin.cancel.viewmodel.RefundUiModel

@Composable
fun PendingRefundCard(
    data: RefundUiModel,
    onForwardClick: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(6.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = "Listing: ${data.listingId}",
                style = MaterialTheme.typography.titleMedium
            )

            Text(text = "Seller: ${data.sellerName}")
            Text(text = "Mobile: ${data.sellerMobile}")

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "Reason: ${data.cancelReason}",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.error
            )

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                text = "Work Status",
                style = MaterialTheme.typography.titleSmall
            )

            StatusRow("Document Verified", data.documentVerified)
            StatusRow("Field Visit Done", data.fieldVisitDone)
            StatusRow("Listing Live", data.listingLive)

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                text = "Cancel Date: ${data.cancelDate}",
                style = MaterialTheme.typography.bodyMedium
            )

            Spacer(modifier = Modifier.height(16.dp))

            Button(
                onClick = onForwardClick,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Forward To Accounting")
            }
        }
    }
}

@Composable
fun StatusRow(label: String, status: Boolean) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(text = label)

        Text(
            text = if (status) "✔" else "✖",
            color = if (status) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error
        )
    }
}
