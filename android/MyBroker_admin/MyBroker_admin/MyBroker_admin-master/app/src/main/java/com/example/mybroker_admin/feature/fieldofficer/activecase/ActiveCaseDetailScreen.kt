package com.example.mybroker_admin.feature.fieldofficer.activecase

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.mybroker_admin.core.navigation.Routes
import com.example.mybroker_admin.feature.fieldofficer.dashboard.FieldDashboardViewModel
import kotlinx.coroutines.delay

@Composable
fun ActiveCaseDetailScreen(
    navController: NavController,
    viewModel: FieldDashboardViewModel = viewModel()
) {
    val state by viewModel.uiState.collectAsState()
    val case = state.activeCase

    if (case == null) {
        Text("No Active Case")
        return
    }

    var remainingTime by remember(case.lockExpiryTime) { mutableStateOf("00:00:00") }

    LaunchedEffect(case.lockExpiryTime) {
        val expiry = case.lockExpiryTime ?: 0L
        while (true) {
            val diff = expiry - System.currentTimeMillis()
            if (diff <= 0L) {
                remainingTime = "00:00:00"
                viewModel.releaseCase()
                break
            }

            val totalSeconds = diff / 1000
            val h = totalSeconds / 3600
            val m = (totalSeconds % 3600) / 60
            val s = totalSeconds % 60
            remainingTime = String.format("%02d:%02d:%02d left", h, m, s)

            delay(1000)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        Text("Active Case Detail", style = MaterialTheme.typography.titleLarge)
        Spacer(modifier = Modifier.height(16.dp))

        Text("Seller: ${case.sellerName}")
        Text("Location: ${case.districtState}")
        Text("Pincode: ${case.pincode}")
        Text("Status: ${case.status}")
        Text("Time: $remainingTime")

        Spacer(modifier = Modifier.height(24.dp))

        Button(
            onClick = {
                val requestId = case.id.toIntOrNull() ?: return@Button
                navController.navigate(Routes.fieldSiteVisit(requestId))
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Start Site Visit")
        }


        Spacer(modifier = Modifier.height(12.dp))

        Button(
            onClick = {
                viewModel.releaseCase()
                navController.popBackStack()
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Release Case")
        }
    }
}
