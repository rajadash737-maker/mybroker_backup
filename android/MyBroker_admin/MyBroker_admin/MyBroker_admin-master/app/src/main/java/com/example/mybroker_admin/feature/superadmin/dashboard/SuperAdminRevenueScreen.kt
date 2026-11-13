package com.example.mybroker_admin.feature.superadmin.dashboard

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import java.text.NumberFormat
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SuperAdminRevenueScreen(navController: NavHostController) {
    val dashboardViewModel = viewModel<SuperAdminDashboardViewModel>()
    val state by dashboardViewModel.state.collectAsState()
    val formatter = NumberFormat.getNumberInstance(Locale.Builder().setLanguage("en").setRegion("IN").build())

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Revenue Details") },
                navigationIcon = {
                    androidx.compose.material3.TextButton(onClick = { navController.popBackStack() }) {
                        Text("Back")
                    }
                }
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .padding(padding)
                .padding(16.dp)
        ) {

            item {
                Text("Revenue Filters", style = MaterialTheme.typography.titleMedium)
                Spacer(modifier = Modifier.height(8.dp))
            }

            item {
                Row(
                    modifier = Modifier.horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    FilterChip(
                        selected = state.rangeType == RevenueRangeType.ALL,
                        onClick = { dashboardViewModel.setRange(RevenueRangeType.ALL) },
                        label = { Text("All") }
                    )
                    FilterChip(
                        selected = state.rangeType == RevenueRangeType.TODAY,
                        onClick = { dashboardViewModel.setRange(RevenueRangeType.TODAY) },
                        label = { Text("Today") }
                    )
                    FilterChip(
                        selected = state.rangeType == RevenueRangeType.WEEK,
                        onClick = { dashboardViewModel.setRange(RevenueRangeType.WEEK) },
                        label = { Text("Week") }
                    )
                    FilterChip(
                        selected = state.rangeType == RevenueRangeType.MONTH,
                        onClick = { dashboardViewModel.setRange(RevenueRangeType.MONTH) },
                        label = { Text("Month") }
                    )
                    FilterChip(
                        selected = state.rangeType == RevenueRangeType.CUSTOM,
                        onClick = { dashboardViewModel.setRange(RevenueRangeType.CUSTOM) },
                        label = { Text("Custom") }
                    )
                }
            }

            if (state.rangeType == RevenueRangeType.CUSTOM) {
                item { Spacer(modifier = Modifier.height(8.dp)) }
                item {
                    OutlinedTextField(
                        value = state.customStart,
                        onValueChange = dashboardViewModel::updateCustomStart,
                        label = { Text("Start (YYYY-MM-DD)") },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
                item { Spacer(modifier = Modifier.height(8.dp)) }
                item {
                    OutlinedTextField(
                        value = state.customEnd,
                        onValueChange = dashboardViewModel::updateCustomEnd,
                        label = { Text("End (YYYY-MM-DD)") },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
                item { Spacer(modifier = Modifier.height(8.dp)) }
                item {
                    Button(
                        onClick = dashboardViewModel::applyCustomRange,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Apply Range")
                    }
                }
            }

            item { Spacer(modifier = Modifier.height(16.dp)) }

            item {
                Text("Revenue Breakdown", style = MaterialTheme.typography.titleMedium)
                Spacer(modifier = Modifier.height(8.dp))
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("Total Revenue: ?${formatter.format(state.totalRevenue)}")
                    Text("Seller Revenue: ?${formatter.format(state.sellerRevenue)}")
                    Text("Buyer Revenue: ?${formatter.format(state.buyerRevenue)}")
                }
            }

            item { Spacer(modifier = Modifier.height(16.dp)) }

            item {
                Text("Transactions", style = MaterialTheme.typography.titleMedium)
                Spacer(modifier = Modifier.height(8.dp))
            }

            if (state.isLoading) {
                item {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
                        CircularProgressIndicator()
                    }
                }
            } else if (!state.errorMessage.isNullOrBlank()) {
                item {
                    Text(state.errorMessage ?: "Failed to load revenue", color = MaterialTheme.colorScheme.error)
                }
            } else if (state.transactions.isEmpty()) {
                item { Text("No transactions found.") }
            } else {
                items(state.transactions.size) { idx ->
                    val txn = state.transactions[idx]
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        elevation = CardDefaults.cardElevation(2.dp)
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Text("Date: ${txn.date}")
                            Text("Type: ${txn.type.uppercase()}")
                            Text("User: ${txn.userName}")
                            Text("Amount: ?${formatter.format(txn.amount)}")
                            Text("Status: ${txn.status}")
                        }
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                }
            }
        }
    }
}
