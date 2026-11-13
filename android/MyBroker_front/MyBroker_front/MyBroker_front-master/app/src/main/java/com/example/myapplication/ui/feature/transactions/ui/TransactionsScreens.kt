package com.example.myapplication.ui.feature.transactions.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import java.text.NumberFormat
import java.util.Locale

@Composable
fun TransactionsScreen(viewModel: TransactionsViewModel, onTransactionClick: (com.example.myapplication.ui.feature.transactions.data.remote.TransactionDto) -> Unit) {
    val state by viewModel.uiState.collectAsState()
    when {
        state.loading -> CircularProgressIndicator(Modifier.padding(24.dp))
        state.error != null -> Text(state.error.orEmpty(), modifier = Modifier.padding(24.dp), color = MaterialTheme.colorScheme.error)
        state.items.isEmpty() -> Text("No transactions yet", modifier = Modifier.padding(24.dp))
        else -> LazyColumn(Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            items(state.items) { item -> Card(Modifier.fillMaxWidth().clickable { onTransactionClick(item) }.padding(horizontal = 12.dp)) {
                Column(Modifier.padding(16.dp)) {
                    Text(item.propertyTitle.ifBlank { "Land transaction" }, style = MaterialTheme.typography.titleMedium)
                    Text(item.location)
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(NumberFormat.getCurrencyInstance(Locale("en", "IN")).format(item.dealAmount))
                        Text(item.paymentStatus.ifBlank { item.dealStatus })
                    }
                }
            } }
        }
    }
}

@Composable
fun TransactionDetailScreen(viewModel: TransactionDetailViewModel, onBack: () -> Unit) {
    val state by viewModel.uiState.collectAsState()
    val item = state.item
    Column(Modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Back", Modifier.clickable(onClick = onBack), color = MaterialTheme.colorScheme.primary)
        when {
            state.loading -> CircularProgressIndicator()
            state.error != null -> Text(state.error.orEmpty(), color = MaterialTheme.colorScheme.error)
            item != null -> {
                Text(item.propertyTitle.ifBlank { "Transaction details" }, style = MaterialTheme.typography.headlineSmall)
                Text("Transaction: ${item.transactionId.orEmpty()}")
                Text("Buyer: ${item.buyerName}")
                Text("Seller: ${item.sellerName}")
                Text("Location: ${item.location}")
                Text("Amount: ${NumberFormat.getCurrencyInstance(Locale("en", "IN")).format(item.dealAmount)}")
                Text("Payment: ${item.paymentStatus}")
                Text("Deal: ${item.dealStatus}")
                item.registryDate?.let { Text("Registry date: $it") }
            }
        }
    }
}
