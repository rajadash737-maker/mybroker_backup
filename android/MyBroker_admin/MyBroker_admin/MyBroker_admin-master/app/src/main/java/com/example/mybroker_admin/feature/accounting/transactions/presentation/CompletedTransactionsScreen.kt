package com.example.mybroker_admin.feature.accounting.transactions.presentation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.mybroker_admin.feature.accounting.transactions.CompletedTransactionsViewModel
import com.example.mybroker_admin.feature.accounting.transactions.model.Transaction
import java.text.DecimalFormat

@Composable
fun CompletedTransactionsRoute(
    onTransactionClick: (String) -> Unit,
    onBack: () -> Unit,
    viewModel: CompletedTransactionsViewModel = viewModel()
) {
    val transactions by viewModel.transactions.collectAsStateWithLifecycle()
    val isLoading by viewModel.isLoading.collectAsStateWithLifecycle()
    val errorMessage by viewModel.errorMessage.collectAsStateWithLifecycle()

    CompletedTransactionsScreen(
        transactions = transactions,
        isLoading = isLoading,
        errorMessage = errorMessage,
        onRetry = viewModel::loadTransactions,
        onTransactionClick = onTransactionClick,
        onBack = onBack
    )
}

@Composable
fun CompletedTransactionsScreen(
    transactions: List<Transaction>,
    isLoading: Boolean,
    errorMessage: String?,
    onRetry: () -> Unit,
    onTransactionClick: (String) -> Unit,
    onBack: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "Completed Transactions",
                style = MaterialTheme.typography.headlineMedium
            )
            TextButton(onClick = onBack) { Text("Back") }
        }

        Spacer(modifier = Modifier.height(12.dp))

        when {
            isLoading -> {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.Center
                ) {
                    CircularProgressIndicator()
                }
            }
            !errorMessage.isNullOrBlank() -> {
                Text(text = errorMessage, color = MaterialTheme.colorScheme.error)
                Spacer(modifier = Modifier.height(8.dp))
                TextButton(onClick = onRetry) { Text("Retry") }
            }
            transactions.isEmpty() -> {
                Text("No transactions found.")
            }
            else -> {
                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(transactions, key = { it.listingId }) { transaction ->
                        TransactionCard(
                            transaction = transaction,
                            onViewDetails = { onTransactionClick(transaction.listingId) }
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun TransactionCard(
    transaction: Transaction,
    onViewDetails: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(4.dp)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Listing ID: LST-${transaction.listingId}",
                    style = MaterialTheme.typography.titleMedium
                )
                StatusPill(text = transaction.status, color = transactionStatusColor(transaction.status))
            }

            Spacer(modifier = Modifier.height(6.dp))
            Text(text = "Seller Name: ${transaction.sellerName}")
            Text(text = "Seller Fee: ${formatMoney(transaction.sellerFee)}")
            StatusPill(
                text = transaction.sellerFeeStatus,
                color = feeStatusColor(transaction.sellerFeeStatus)
            )

            Spacer(modifier = Modifier.height(6.dp))
            Text(text = "Buyer Name: ${transaction.buyerName ?: "Not Booked Yet"}")
            Text(text = "Buyer Fee: ${transaction.buyerFee?.let { formatMoney(it) } ?: "---"}")
            StatusPill(
                text = transaction.buyerFeeStatus,
                color = feeStatusColor(transaction.buyerFeeStatus)
            )
            Text(text = "Date: ${transaction.date}")

            Spacer(modifier = Modifier.height(4.dp))
            TextButton(onClick = onViewDetails) { Text("View Details") }
        }
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

private fun completedColor(): Color = Color(0xFF2E7D32)

private fun pendingColor(): Color = Color(0xFFC62828)

private fun transactionStatusColor(status: String): Color {
    return if (status.equals("COMPLETED", ignoreCase = true)) completedColor() else Color(0xFFF9A825)
}

private fun feeStatusColor(status: String): Color {
    return if (status.equals("PAID", ignoreCase = true)) completedColor() else pendingColor()
}

private fun formatMoney(value: Double): String {
    return "INR ${DecimalFormat("#,##0.##").format(value)}"
}
