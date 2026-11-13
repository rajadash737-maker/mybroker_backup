package com.example.mybroker_admin.feature.fieldofficer.available

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.example.mybroker_admin.feature.fieldofficer.dashboard.FieldDashboardViewModel

@Composable
fun AvailableCasesScreen(
    navController: NavController,
    viewModel: FieldDashboardViewModel = viewModel()
) {

    val state by viewModel.uiState.collectAsState()

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {

        items(state.availableCases) { case ->

            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 8.dp)
            ) {

                Column(Modifier.padding(16.dp)) {

                    Text(case.sellerName, fontWeight = FontWeight.Bold)
                    Text("Location: ${case.districtState}")
                    Text("Pincode: ${case.pincode}")

                    Spacer(modifier = Modifier.height(8.dp))

                    Button(
                        onClick = {
                            viewModel.claimCase(case)
                            navController.popBackStack()
                        },
                        enabled = state.activeCase == null,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Claim Case")
                    }
                }
            }
        }
    }
}
