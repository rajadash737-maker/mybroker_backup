package com.example.mybroker_admin.feature.registry.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.example.mybroker_admin.core.navigation.Routes
import com.example.mybroker_admin.feature.registry.RegistryDashboardViewModel
import com.example.mybroker_admin.feature.registry.components.RegistryUpcomingCard

@Composable
fun RegistryDashboardScreen(
    navController: NavController,
    viewModel: RegistryDashboardViewModel = viewModel()
) {
    val state by viewModel.uiState.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        Text(
            text = "Registry Dashboard",
            style = MaterialTheme.typography.titleLarge
        )

        Spacer(modifier = Modifier.height(16.dp))

        val upcoming = state.upcoming
        when {
            state.isLoading -> CircularProgressIndicator()
            state.error != null -> Text(state.error ?: "Failed to load")
            state.items.isNotEmpty() -> {
                LazyColumn {
                    items(state.items, key = { it.id }) { item ->
                        RegistryUpcomingCard(
                            assignment = item,
                            onClick = {
                                navController.navigate(Routes.registryDetail(item.id))
                            }
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                    }
                }
            }
            else -> Text("No upcoming registry visit")
        }
    }
}
