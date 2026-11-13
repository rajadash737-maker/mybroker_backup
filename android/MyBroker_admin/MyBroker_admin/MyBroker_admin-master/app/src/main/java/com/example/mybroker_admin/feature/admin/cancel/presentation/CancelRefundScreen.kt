package com.example.mybroker_admin.feature.admin.cancel.presentation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.mybroker_admin.feature.admin.cancel.presentation.components.CancelTabRow
import com.example.mybroker_admin.feature.admin.cancel.presentation.components.PendingRefundCard
import com.example.mybroker_admin.feature.admin.cancel.presentation.components.SuccessRefundCard
import com.example.mybroker_admin.feature.admin.cancel.presentation.state.RefundTab
import com.example.mybroker_admin.feature.admin.cancel.viewmodel.CancelRefundViewModel

@Composable
fun CancelRefundScreen(
    viewModel: CancelRefundViewModel = viewModel()
) {
    val state by viewModel.state.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(state.errorMessage) {
        state.errorMessage?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearError()
        }
    }

    LaunchedEffect(state.successMessage) {
        state.successMessage?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearSuccess()
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        SnackbarHost(hostState = snackbarHostState)

        Text(
            text = "Cancel & Refund Management",
            style = MaterialTheme.typography.headlineSmall
        )

        Spacer(modifier = Modifier.height(16.dp))

        CancelTabRow(
            selectedTab = state.selectedTab,
            onTabSelected = { viewModel.onTabSelected(it) }
        )

        Spacer(modifier = Modifier.height(16.dp))

        if (state.isLoading) {
            CircularProgressIndicator()
            return@Column
        }

        when (state.selectedTab) {
            RefundTab.PENDING -> {
                if (state.pendingList.isEmpty()) {
                    Text("No Pending Refund Cases")
                } else {
                    LazyColumn(
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        items(state.pendingList) { item ->
                            PendingRefundCard(
                                data = item,
                                onForwardClick = {
                                    viewModel.forwardToAccounting(item.id)
                                }
                            )
                        }
                    }
                }
            }

            RefundTab.SUCCESS -> {
                if (state.successList.isEmpty()) {
                    Text("No Successful Refund Cases")
                } else {
                    LazyColumn(
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        items(state.successList) { item ->
                            SuccessRefundCard(data = item)
                        }
                    }
                }
            }
        }
    }
}
