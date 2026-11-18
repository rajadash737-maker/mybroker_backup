package com.example.myapplication.ui.feature.buyer.payment

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.example.myapplication.network.ApiClient
import com.example.myapplication.ui.feature.buyer.data.remote.LandApi
import com.example.myapplication.ui.feature.buyer.data.remote.dto.BuyerPropertyBookingRefundDto
import com.example.myapplication.ui.feature.buyer.data.remote.dto.BuyerRefundUpiRequestDto
import kotlinx.coroutines.launch
import java.text.NumberFormat
import java.util.Locale

@Composable
fun BuyerBookingRefundScreen(bookingId: Int, onBack: () -> Unit) {
    val api = remember { ApiClient.createService(LandApi::class.java) }
    val scope = rememberCoroutineScope()
    var details by remember { mutableStateOf<BuyerPropertyBookingRefundDto?>(null) }
    var upi by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    fun load() {
        scope.launch {
            loading = true; error = null
            runCatching { api.getBookingRefund(bookingId) }
                .onSuccess { details = it }
                .onFailure { error = it.message ?: "Could not load refund details" }
            loading = false
        }
    }
    LaunchedEffect(bookingId) { load() }
    Column(Modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Back", Modifier.clickable(onClick = onBack), color = MaterialTheme.colorScheme.primary)
        Text("Booking Cancellation & Refund", style = MaterialTheme.typography.headlineSmall)
        if (loading) CircularProgressIndicator()
        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        details?.let { d ->
            Text("Booking #${d.bookingId} · Listing #${d.listingId}")
            Text("Status: ${d.bookingStatus.replace('_', ' ').uppercase()}")
            Text("Cancellation reason: ${d.cancellationReason}")
            if (d.refundDecision == "NO_REFUND") {
                Text("No Refund", style = MaterialTheme.typography.titleMedium)
            } else {
                Text("Approved refund: ${rupees(d.approvedRefundAmount)}")
                Text("Refund status: ${d.refundStatus.replace('_', ' ')}")
                if (d.refundStatus == "AWAITING_BUYER_DETAILS") {
                    Text("Enter your UPI ID so Accounting can process the approved external refund.")
                    OutlinedTextField(
                        value = upi, onValueChange = { upi = it.trim() },
                        label = { Text("UPI ID") }, modifier = Modifier.fillMaxWidth(),
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email)
                    )
                    Button(onClick = {
                        val cleaned = upi.trim()
                        if (!Regex("^[A-Za-z0-9._-]{2,256}@[A-Za-z0-9]{2,64}$").matches(cleaned)) {
                            error = "Enter a valid UPI ID."
                        } else scope.launch {
                            loading = true; error = null
                            runCatching { api.submitBookingRefundUpi(bookingId, BuyerRefundUpiRequestDto(cleaned)) }
                                .onSuccess { details = it; upi = "" }
                                .onFailure { error = it.message ?: "Could not submit UPI ID" }
                            loading = false
                        }
                    }, enabled = !loading, modifier = Modifier.fillMaxWidth()) { Text("Submit UPI ID") }
                }
                if (d.refundStatus == "PENDING_ACCOUNTING") Text("Awaiting Accounting refund")
                if (d.refundStatus == "CONFIRMED") {
                    Text("REFUNDED SUCCESSFULLY · ${rupees(d.actualRefundedAmount ?: 0.0)}")
                    Text("Transaction: ${d.transactionReference.orEmpty()}")
                    Text("Confirmed: ${d.accountingConfirmedAt.orEmpty()}")
                }
                if (d.refundStatus == "FAILED") Text("Accounting could not complete this refund. Contact support.")
            }
        }
    }
}

private fun rupees(value: Double): String = NumberFormat.getCurrencyInstance(Locale("en", "IN")).format(value)
