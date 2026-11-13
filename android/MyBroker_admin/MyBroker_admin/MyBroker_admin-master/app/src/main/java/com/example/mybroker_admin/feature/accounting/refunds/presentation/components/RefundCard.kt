package com.example.mybroker_admin.feature.accounting.refunds.presentation.components

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.mybroker_admin.feature.accounting.refunds.model.RefundItem

@Composable
fun RefundCard(
    data: RefundItem,
    isHistory: Boolean = false,
    onConfirm: ((Int, String) -> Unit)? = null
) {
    var refundAmount by remember { mutableStateOf("") }
    var transactionId by remember { mutableStateOf("") }

    val amount = refundAmount.toIntOrNull()
    val canConfirm = amount != null && amount > 0 && transactionId.isNotBlank()

    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(6.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("Listing ID: ${data.listingId}")
            Text("Seller: ${data.sellerName}")
            Text("Mobile: ${data.sellerMobile}")
            Text("Cancel Date: ${data.cancelDate}")
            Text("Total Paid: ₹${data.totalPaid}")

            Text("Seller UPI (Refund To): ${data.sellerUpiId ?: "--"}")

            if (data.cancelReason.isNotBlank()) {
                Spacer(modifier = Modifier.height(6.dp))
                Text("Reason: ${data.cancelReason}", color = MaterialTheme.colorScheme.error)
            }

            Spacer(modifier = Modifier.height(8.dp))

            if (data.isAdminInvolved) {
                Text("Admin Involved", color = MaterialTheme.colorScheme.primary)
                Text("Admin Name: ${data.adminName.orEmpty()}")
                Text("Admin Mobile: ${data.adminMobile.orEmpty()}")
                Text("Admin Status: ${data.adminStatus.orEmpty()}")
            } else {
                Text(
                    "No Admin Involved (Direct Cancel)",
                    color = MaterialTheme.colorScheme.error
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            if (!isHistory) {
                OutlinedTextField(
                    value = refundAmount,
                    onValueChange = { refundAmount = it.filter(Char::isDigit) },
                    label = { Text("Refund Amount") },
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(8.dp))

                OutlinedTextField(
                    value = transactionId,
                    onValueChange = { transactionId = it },
                    label = { Text("Transaction ID") },
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(12.dp))

                Button(
                    onClick = { onConfirm?.invoke(amount!!, transactionId.trim()) },
                    enabled = canConfirm,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Confirm Refund")
                }
            } else {
                Text(
                    "Refund Amount: ₹${data.refundAmount ?: 0}",
                    color = MaterialTheme.colorScheme.primary
                )
                Text("Transaction ID: ${data.transactionId.orEmpty()}")
                Text("Refunded Date: ${data.refundedDate.orEmpty()}")
                Text("Status: Completed", color = MaterialTheme.colorScheme.primary)
            }
        }
    }
}
