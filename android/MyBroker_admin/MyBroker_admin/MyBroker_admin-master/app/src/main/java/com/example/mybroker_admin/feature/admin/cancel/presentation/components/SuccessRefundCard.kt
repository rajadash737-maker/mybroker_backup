package com.example.mybroker_admin.feature.admin.cancel.presentation.components

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
import com.example.mybroker_admin.feature.admin.cancel.viewmodel.RefundUiModel

@Composable
fun SuccessRefundCard(
    data: RefundUiModel
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(4.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(text = "Listing: ${data.listingId}")
            Text(text = "Seller: ${data.sellerName}")
            Text(text = "Mobile: ${data.sellerMobile}")
            Text(text = "Cancel Date: ${data.cancelDate}")

            if (data.cancelReason.isNotBlank()) {
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = "Reason: ${data.cancelReason}",
                    color = MaterialTheme.colorScheme.error
                )
            }

            if (!data.refundDate.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(6.dp))
                Text(text = "Refund Date: ${data.refundDate}")
            }

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "Seller Current Status: ${data.sellerCurrentStatus ?: "-"}",
                color = MaterialTheme.colorScheme.primary
            )

            Spacer(modifier = Modifier.height(4.dp))

            Text(
                text = "Refund Status: ${data.refundStatus ?: "refund_successful"}",
                color = MaterialTheme.colorScheme.primary
            )
        }
    }
}
