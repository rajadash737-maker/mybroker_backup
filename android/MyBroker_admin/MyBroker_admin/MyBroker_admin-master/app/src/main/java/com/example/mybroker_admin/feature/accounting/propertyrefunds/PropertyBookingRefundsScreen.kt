package com.example.mybroker_admin.feature.accounting.propertyrefunds

import androidx.compose.foundation.clickable
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
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.remote.dto.PropertyBookingRefundDetailDto
import com.example.mybroker_admin.data.remote.dto.PropertyBookingRefundItemDto
import com.example.mybroker_admin.data.repository.AccountingListingRepository
import kotlinx.coroutines.launch
import java.text.DecimalFormat

@Composable
fun PropertyBookingRefundsScreen(onBack: () -> Unit) {
    val repo = remember { AccountingListingRepository(ApiClient.accountingListingApi) }
    val scope = rememberCoroutineScope()
    var rows by remember { mutableStateOf<List<PropertyBookingRefundItemDto>>(emptyList()) }
    var detail by remember { mutableStateOf<PropertyBookingRefundDetailDto?>(null) }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var amount by remember(detail?.approved_refund_amount) { mutableStateOf(detail?.approved_refund_amount?.toString().orEmpty()) }
    var reference by remember { mutableStateOf("") }
    var note by remember { mutableStateOf("") }
    var failReason by remember { mutableStateOf("") }
    var confirmFail by remember { mutableStateOf(false) }
    var showHistory by remember { mutableStateOf(false) }

    fun refresh() {
        scope.launch {
            loading = true; error = null
            runCatching { repo.getPropertyBookingRefunds(includeHistory = showHistory) }
                .onSuccess { rows = it.items }
                .onFailure { error = it.message ?: "Could not load property booking refunds" }
            loading = false
        }
    }
    LaunchedEffect(Unit) { refresh() }
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("Property Booking Refunds", style = MaterialTheme.typography.headlineSmall)
            TextButton(onClick = { if (detail != null) detail = null else onBack() }) { Text(if (detail != null) "Queue" else "Back") }
        }
        if (detail == null) TextButton(onClick = { showHistory = !showHistory; refresh() }) {
            Text(if (showHistory) "Show pending queue" else "Show refund history")
        }
        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        if (loading) CircularProgressIndicator()
        if (detail == null) {
            if (!loading && rows.isEmpty()) Text("No property booking refunds are awaiting Accounting.")
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(rows, key = { it.refund_id }) { item ->
                    Card(Modifier.fillMaxWidth().clickable {
                        scope.launch {
                            loading = true; error = null
                            runCatching { repo.getPropertyBookingRefund(item.refund_id) }
                                .onSuccess { detail = it }
                                .onFailure { error = it.message ?: "Could not load refund detail" }
                            loading = false
                        }
                    }) {
                        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                            Text("Booking #${item.booking_id} · Listing #${item.listing_id} ${item.listing_code.orEmpty()}", style = MaterialTheme.typography.titleSmall)
                            Text(item.property_name ?: "Property")
                            Text("${item.buyer_name} · ${item.buyer_mobile}")
                            Text("Buyer UPI: ${item.buyer_upi_id ?: "Not submitted"}")
                            Text("Captured ₹${money(item.original_captured_amount)} · Approved ₹${money(item.approved_refund_amount)}")
                            Text("${item.refund_status} · ${item.cancelled_at}")
                            Text("Reason: ${item.cancellation_reason}")
                        }
                    }
                }
            }
        } else {
            val d = detail!!
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                item {
                    Text("${d.property_name ?: "Property"} · ${d.listing_code.orEmpty()}", style = MaterialTheme.typography.titleLarge)
                    Text("Booking #${d.booking_id} · Listing #${d.listing_id} · Payment record #${d.payment_order_id}")
                    Text("Buyer: ${d.buyer_name} · ${d.buyer_mobile}")
                    Text("Original captured: ₹${money(d.original_captured_amount)}")
                    Text("Approved refund: ₹${money(d.approved_refund_amount)}")
                    Text("Status: ${d.refund_status} · Cancelled: ${d.cancelled_at}")
                    Text("Reason: ${d.cancellation_reason}")
                    Text("Buyer UPI: ${d.buyer_upi_id ?: "Not available"}", style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(8.dp))
                    Text("Refund history", style = MaterialTheme.typography.titleMedium)
                    d.history.forEach { Text("${it.created_at} · ${it.event_type}: ${it.note.orEmpty()}") }
                    if (d.refund_status == "PENDING_ACCOUNTING" || d.refund_status == "FAILED") {
                        if (d.refund_status == "FAILED") {
                            Text("Previous transfer failed. Record a new transaction here after resolving the failed transfer.")
                        }
                        OutlinedTextField(amount, { amount = it }, label = { Text("Actual refund amount") }, modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(reference, { reference = it }, label = { Text("UPI / bank transaction reference") }, modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(note, { note = it }, label = { Text("Confirmation note (optional)") }, modifier = Modifier.fillMaxWidth())
                        Button(onClick = {
                            val parsed = amount.toDoubleOrNull()
                            if (parsed == null || parsed != d.approved_refund_amount || reference.trim().length < 3) error = "Enter the approved amount exactly and a transaction reference."
                            else if (!loading) scope.launch {
                                if (loading) return@launch
                                loading = true
                                error = null
                                runCatching {
                                    repo.confirmPropertyBookingRefund(
                                        d.refund_id,
                                        parsed,
                                        reference.trim(),
                                        note.trim().ifEmpty { null }
                                    )
                                }
                                    .onSuccess { detail = it; refresh() }
                                    .onFailure { error = it.message ?: "Confirmation failed" }
                                loading = false
                            }
                        }, enabled = !loading, modifier = Modifier.fillMaxWidth()) { Text("Record External Refund") }
                        if (d.refund_status == "PENDING_ACCOUNTING") {
                            OutlinedButton(onClick = { confirmFail = true }, enabled = !loading, modifier = Modifier.fillMaxWidth()) { Text("Mark Refund Failed") }
                        }
                    } else if (d.refund_status == "CONFIRMED") {
                        Text("Refund recorded as externally paid: ₹${money(d.actual_refunded_amount ?: 0.0)} · ${d.transaction_reference.orEmpty()} · ${d.accounting_confirmed_at.orEmpty()}")
                    }
                }
            }
        }
    }
    if (confirmFail) {
        AlertDialog(
            onDismissRequest = { if (!loading) confirmFail = false },
            title = { Text("Mark refund failed") },
            text = {
                OutlinedTextField(
                    value = failReason,
                    onValueChange = { failReason = it },
                    label = { Text("Reason") }
                )
            },
            confirmButton = {
                TextButton(
                    enabled = !loading,
                    onClick = {
                        val selectedRefund = detail
                        if (selectedRefund == null) {
                            error = "Refund details are unavailable."
                        } else if (failReason.trim().length < 3) {
                            error = "Enter a reason for failure."
                        } else if (!loading) {
                            scope.launch {
                                if (loading) return@launch
                                loading = true
                                error = null
                                confirmFail = false
                                runCatching {
                                    repo.failPropertyBookingRefund(selectedRefund.refund_id, failReason.trim())
                                }
                                    .onSuccess { detail = it; refresh() }
                                    .onFailure { error = it.message ?: "Could not update refund" }
                                loading = false
                            }
                        }
                    }
                ) {
                    Text(if (loading) "Saving..." else "Confirm")
                }
            },
            dismissButton = {
                TextButton(enabled = !loading, onClick = { confirmFail = false }) {
                    Text("Cancel")
                }
            }
        )
    }
}

private fun money(value: Double): String = DecimalFormat("#,##0.00").format(value)
