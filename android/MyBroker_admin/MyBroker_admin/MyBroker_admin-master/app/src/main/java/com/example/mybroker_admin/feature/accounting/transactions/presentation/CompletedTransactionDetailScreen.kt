package com.example.mybroker_admin.feature.accounting.transactions.presentation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.mybroker_admin.feature.accounting.transactions.CompletedTransactionsViewModel
import com.example.mybroker_admin.feature.accounting.transactions.model.PaymentInfo
import com.example.mybroker_admin.feature.accounting.transactions.model.TransactionDetail
import java.text.DecimalFormat

@Composable
fun CompletedTransactionDetailRoute(
    listingId: String,
    onBack: () -> Unit,
    viewModel: CompletedTransactionsViewModel = viewModel()
) {
    val detail by viewModel.detail.collectAsStateWithLifecycle()
    val isLoading by viewModel.detailLoading.collectAsStateWithLifecycle()
    val errorMessage by viewModel.detailError.collectAsStateWithLifecycle()
    val lifecycleOwner = LocalLifecycleOwner.current

    LaunchedEffect(listingId) {
        viewModel.loadTransactionDetail(listingId)
    }

    DisposableEffect(lifecycleOwner, listingId) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                viewModel.loadTransactionDetail(listingId)
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    CompletedTransactionDetailScreen(
        detail = detail,
        isLoading = isLoading,
        errorMessage = errorMessage,
        onBack = onBack
    )
}

@Composable
fun CompletedTransactionDetailScreen(
    detail: TransactionDetail?,
    isLoading: Boolean,
    errorMessage: String?,
    onBack: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "Transaction Details",
                style = MaterialTheme.typography.headlineMedium
            )
            TextButton(onClick = onBack) { Text("Back") }
        }

        Spacer(modifier = Modifier.height(12.dp))

        if (isLoading) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.Center
            ) {
                CircularProgressIndicator()
            }
            return
        }

        if (!errorMessage.isNullOrBlank()) {
            Text(text = errorMessage, color = MaterialTheme.colorScheme.error)
            return
        }

        if (detail == null) {
            Text("Transaction not found.")
            return
        }

        val transaction = detail.transaction
        val paymentDetails = detail.paymentDetails

        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            elevation = CardDefaults.cardElevation(4.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "Listing ID: LST-${transaction.listingId}",
                    style = MaterialTheme.typography.titleMedium
                )
                Spacer(modifier = Modifier.height(8.dp))

                InfoRow(label = "Land Price", value = detail.landPriceNote)
                Spacer(modifier = Modifier.height(8.dp))

                InfoRow(
                    label = "Seller",
                    value = transaction.sellerName
                )
                StatusRow(
                    label = "Seller Fee",
                    value = formatMoney(transaction.sellerFee),
                    status = transaction.sellerFeeStatus
                )

                Spacer(modifier = Modifier.height(8.dp))

                InfoRow(
                    label = "Buyer",
                    value = transaction.buyerName ?: "Not Booked Yet"
                )

                StatusRow(
                    label = "Buyer Fee",
                    value = transaction.buyerFee?.let { formatMoney(it) } ?: "---",
                    status = transaction.buyerFeeStatus
                )

                Spacer(modifier = Modifier.height(8.dp))
                Text(text = "Land payment is done outside the app")
                Spacer(modifier = Modifier.height(8.dp))
                StatusRow(
                    label = "Final Status",
                    value = detail.finalStatus,
                    status = detail.finalStatus
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        SectionTitle(text = "Payment Details")
        Spacer(modifier = Modifier.height(8.dp))

        PaymentCard(
            title = "Seller Payment",
            paymentInfo = paymentDetails.seller,
            showNotBooked = false
        )

        Spacer(modifier = Modifier.height(12.dp))

        val buyerNotBooked = transaction.buyerName.isNullOrBlank() || paymentDetails.buyer == null
        PaymentCard(
            title = "Buyer Payment",
            paymentInfo = paymentDetails.buyer,
            showNotBooked = buyerNotBooked
        )
    }
}

@Composable
private fun SectionTitle(text: String) {
    Text(
        text = text,
        style = MaterialTheme.typography.titleMedium
    )
}

@Composable
private fun PaymentCard(
    title: String,
    paymentInfo: PaymentInfo?,
    showNotBooked: Boolean
) {
    val method = paymentInfo?.method ?: "--"
    val transactionId = paymentInfo?.transactionId ?: "--"
    val paidAt = paymentInfo?.paidAt ?: "--"
    val status = paymentInfo?.status ?: "PENDING"

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(2.dp)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(text = title, style = MaterialTheme.typography.titleSmall)
                if (showNotBooked) {
                    Text(text = "Not Booked Yet", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            InfoRow(label = "Payment Method", value = if (showNotBooked) "--" else method)
            Spacer(modifier = Modifier.height(6.dp))
            CopyableInfoRow(
                label = "Transaction ID",
                value = if (showNotBooked) "--" else transactionId,
                canCopy = !showNotBooked && transactionId != "--"
            )
            Spacer(modifier = Modifier.height(6.dp))
            InfoRow(label = "Payment Date & Time", value = if (showNotBooked) "--" else paidAt)
            Spacer(modifier = Modifier.height(6.dp))
            StatusRow(label = "Payment Status", value = status, status = status)
        }
    }
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(text = label)
        Text(text = value)
    }
}

@Composable
private fun CopyableInfoRow(label: String, value: String, canCopy: Boolean) {
    val clipboardManager = LocalClipboardManager.current
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(text = label)
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(text = value)
            IconButton(
                onClick = { clipboardManager.setText(AnnotatedString(value)) },
                enabled = canCopy
            ) {
                Icon(
                    imageVector = Icons.Default.ContentCopy,
                    contentDescription = "Copy transaction id"
                )
            }
        }
    }
}

@Composable
private fun StatusRow(label: String, value: String, status: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(text = "$label: $value")
        StatusPill(text = status.uppercase(), color = statusColor(status))
    }
}

@Composable
private fun StatusPill(text: String, color: Color) {
    Surface(
        color = color.copy(alpha = 0.15f),
        contentColor = color,
        shape = MaterialTheme.shapes.small
    ) {
        Text(
            text = text,
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
            style = MaterialTheme.typography.labelMedium
        )
    }
}

private fun statusColor(status: String): Color {
    return when {
        status.equals("COMPLETED", ignoreCase = true) || status.equals("PAID", ignoreCase = true) ->
            Color(0xFF2E7D32)
        status.equals("WAITING_BUYER", ignoreCase = true) || status.equals("PENDING", ignoreCase = true) ->
            Color(0xFFF9A825)
        else -> Color(0xFFC62828)
    }
}

private fun formatMoney(value: Double): String {
    return "INR ${DecimalFormat("#,##0.##").format(value)}"
}
