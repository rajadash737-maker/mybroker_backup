package com.example.mybroker_admin.feature.admin.approvals.presentation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.feature.admin.approvals.model.FinalApprovalListing
import com.example.mybroker_admin.feature.admin.approvals.presentation.components.FinalApprovalCard
import com.example.mybroker_admin.feature.admin.listings.AdminListingsViewModel
import java.text.SimpleDateFormat
import java.util.Locale

@Composable
fun FinalApprovalRoute(
    vm: AdminListingsViewModel = viewModel()
) {
    val listings by vm.listings.collectAsStateWithLifecycle()
    val isLoading by vm.isLoading.collectAsStateWithLifecycle()
    val errorMessage by vm.errorMessage.collectAsStateWithLifecycle()
    val actionMessage by vm.actionMessage.collectAsStateWithLifecycle()

    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(Unit) {
        vm.loadFinalApprovalCases()
    }

    LaunchedEffect(actionMessage) {
        actionMessage?.let {
            snackbarHostState.showSnackbar(it)
            vm.clearActionMessage()
        }
    }

    val finalItems = listings.map {
        FinalApprovalListing(
            id = it.id,
            sellerName = it.sellerName,
            sellerMobile = it.sellerMobile,
            location = it.locationText,
            officerName = it.assignedOfficer ?: "N/A",
            officerMobile = it.officerMobile ?: "N/A",
            visitDate = formatVisitDate(it.lockTime),
            recommendation = "APPROVE",
            reportSummary = "",
            fieldPhotos = listOfNotNull(
                ApiClient.absoluteUrl(it.visitPhotoUrl)?.takeIf { url -> url.isNotBlank() }
            )
        )
    }

    FinalApprovalScreen(
        items = finalItems,
        isLoading = isLoading,
        errorMessage = errorMessage,
        onApproveGoLive = { id -> vm.approveGoLive(id) },
        onReject = { id, reason -> vm.rejectFinal(id, reason) },
        onReassign = { id -> vm.reassignToFieldOfficer(id) },
        snackbarHostState = snackbarHostState
    )
}

@Composable
fun FinalApprovalScreen(
    items: List<FinalApprovalListing>,
    isLoading: Boolean,
    errorMessage: String?,
    onApproveGoLive: (Int) -> Unit,
    onReject: (Int, String) -> Unit,
    onReassign: (Int) -> Unit,
    snackbarHostState: SnackbarHostState
) {
    Scaffold(
        snackbarHost = { SnackbarHost(hostState = snackbarHostState) }
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                Text(
                    text = "Field Verified (Final Approval)",
                    style = MaterialTheme.typography.titleLarge
                )
            }

            when {
                isLoading -> item { CircularProgressIndicator() }
                !errorMessage.isNullOrBlank() -> item {
                    Text(errorMessage, color = MaterialTheme.colorScheme.error)
                }
                items.isEmpty() -> item { Text("No field verified cases found.") }
                else -> items(items, key = { it.id }) { listing ->
                    FinalApprovalCard(
                        listing = listing,
                        onApproveGoLive = { onApproveGoLive(listing.id) },
                        onReject = { reason -> onReject(listing.id, reason) },
                        onReassign = { onReassign(listing.id) }
                    )
                }
            }
        }
    }
}

private fun formatVisitDate(raw: String?): String {
    if (raw.isNullOrBlank()) return "-"
    val cleaned = raw.trim()
        .replace("Z", "")
        .replace(Regex("[+-]\\d{2}:?\\d{2}$"), "")
        .let { value ->
            val dot = value.indexOf(".")
            if (dot >= 0) value.substring(0, dot) else value
        }

    val inputFormats = listOf(
        SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.ENGLISH),
        SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.ENGLISH)
    )
    val outputFormat = SimpleDateFormat("dd MMMM yyyy, hh.mm a", Locale.ENGLISH)

    for (fmt in inputFormats) {
        runCatching {
            val date = fmt.parse(cleaned) ?: return@runCatching null
            val formatted = outputFormat.format(date)
            return formatted.replace("AM", "am").replace("PM", "pm")
        }
    }

    return raw
}
