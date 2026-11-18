package com.example.myapplication.ui.feature.sitevisit.presentation

import android.app.Activity
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.clickable
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.rememberDatePickerState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccessTime
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.example.myapplication.BuildConfig
import com.example.myapplication.network.ApiClient
import com.example.myapplication.ui.feature.buyer.payment.RazorpayPaymentBus
import com.example.myapplication.ui.feature.sitevisit.data.SiteVisitRepository
import com.example.myapplication.ui.feature.sitevisit.data.SiteVisitBookingDto
import com.razorpay.Checkout
import org.json.JSONObject
import java.time.Instant
import java.time.LocalDate
import java.time.LocalTime
import java.time.ZoneOffset

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SiteVisitScreen(listingId: Int, onBack: () -> Unit, onViewStatus: () -> Unit = onBack, selectedBookingId: Int? = null) {
    val context = LocalContext.current
    val viewModel = remember { SiteVisitViewModel() }
    val state by viewModel.state.collectAsState()
    var date by remember { mutableStateOf("") }
    var hour by remember { mutableStateOf<String?>(null) }
    var minute by remember { mutableStateOf<String?>(null) }
    var showDatePicker by remember { mutableStateOf(false) }
    var visitors by remember { mutableStateOf("1") }
    var address by remember { mutableStateOf("") }
    var message by remember { mutableStateOf("") }
    var termsAccepted by remember { mutableStateOf(false) }
    var showTerms by remember { mutableStateOf(false) }
    var cancellationTarget by remember { mutableStateOf<SiteVisitBookingDto?>(null) }
    var cancellationReason by remember { mutableStateOf("") }
    var cancellationUpiId by remember(cancellationTarget?.id) { mutableStateOf("") }
    var cancellationValidationAttempted by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        ApiClient.init(context.applicationContext)
        if (listingId > 0) viewModel.load(listingId) else viewModel.refresh()
        RazorpayPaymentBus.events.collect { result ->
            if (result.success) viewModel.paymentSuccess(result.paymentId, result.orderId, result.signature)
            else viewModel.paymentFailure()
        }
    }
    LaunchedEffect(state.cancelResponse?.bookingId) {
        if (state.cancelResponse?.bookingId == cancellationTarget?.id) {
            cancellationTarget = null
            cancellationReason = ""
            cancellationUpiId = ""
            cancellationValidationAttempted = false
        }
    }
    LaunchedEffect(state.order?.orderId) {
        val order = state.order ?: return@LaunchedEffect
        val activity = context as? Activity ?: return@LaunchedEffect
        runCatching {
            val options = JSONObject().apply {
                put("name", "MyBrokerr")
                put("description", "Site Visit")
                put("order_id", order.orderId)
                put("amount", order.amountPaise)
                put("currency", order.currency)
            }
            Checkout().apply { setKeyID(BuildConfig.RAZORPAY_KEY_ID) }.open(activity, options)
            viewModel.checkoutLaunched()
        }.onFailure { viewModel.paymentFailure() }
    }

    val dateTimeError = SiteVisitBookingTime.validate(date, hour, minute, LocalDate.now(), LocalTime.now())
    val formCanSubmit = SiteVisitUiRules.canSubmit(
        listingId = listingId,
        feeLoaded = state.feeRupees != null,
        date = date,
        hour = hour,
        minute = minute,
        visitors = visitors,
        address = address,
        today = LocalDate.now(),
        now = LocalTime.now()
    )

    Scaffold { inset ->
        Column(
            Modifier.fillMaxSize().padding(inset).padding(20.dp).verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(
                    when {
                        listingId <= 0 -> "My Site Visits"
                        state.booking != null -> "Booking Summary"
                        else -> "Schedule a Site Visit"
                    },
                    style = MaterialTheme.typography.headlineSmall
                )
                TextButton(onClick = onBack) { Text("Back") }
            }
            if (listingId <= 0) {
                TextButton(onClick = { viewModel.refresh() }, enabled = !state.loading) {
                    Icon(Icons.Filled.Refresh, contentDescription = null)
                    Text("Refresh my bookings")
                }
                state.message?.let { Text(it, color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.bodySmall) }
                if (state.loading) CircularProgressIndicator(Modifier.align(Alignment.CenterHorizontally))
                state.error?.let { error ->
                    Text(error, color = MaterialTheme.colorScheme.error)
                    TextButton(onClick = { viewModel.refresh() }) { Text("Retry") }
                }
                if (!state.loading && state.error == null && state.bookings.isEmpty()) {
                    Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
                        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text("No Site Visits yet", style = MaterialTheme.typography.titleMedium)
                            Text("Your requested visits and their latest status will appear here.")
                        }
                    }
                }
                state.bookings.sortedByDescending { it.id == selectedBookingId }.forEach { booking ->
                    SiteVisitStatusCard(booking, onCancel = {
                        viewModel.clearMessages()
                        cancellationTarget = booking
                        cancellationReason = ""
                        cancellationUpiId = ""
                        cancellationValidationAttempted = false
                    }, onResubmit = { target, correctedDate, correctedTime, correctedVisitors, correctedAddress, correctedMessage ->
                        viewModel.resubmitCorrection(target.id, correctedDate, correctedTime, correctedVisitors, correctedAddress, correctedMessage)
                    }, onSubmitRefund = { target, upiId ->
                        viewModel.submitRefundDetails(target.id, upiId)
                    }, busy = state.submitting, highlighted = booking.id == selectedBookingId)
                }
                if (state.bookings.isNotEmpty()) {
                    Text("Seller and assigned Field Officer details are not provided by the current buyer booking API.", style = MaterialTheme.typography.bodySmall)
                }
            } else if (state.booking != null) {
                val booking = state.booking!!
                BookingSummaryContent(
                    booking = booking,
                    termsAccepted = termsAccepted,
                    busy = state.submitting || state.checkoutInProgress,
                    error = state.error,
                    message = state.message,
                    onTermsClick = { showTerms = true },
                    onTermsAccepted = { termsAccepted = it },
                    onPay = { viewModel.createOrder(booking.id) },
                    onViewStatus = onViewStatus
                )
            } else if (state.listingLookupLoading) {
                CircularProgressIndicator(Modifier.align(Alignment.CenterHorizontally))
                Text("Checking your existing Site Visit bookings before showing the request form.")
            } else if (state.listingLookupError != null) {
                state.listingLookupError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                TextButton(onClick = { viewModel.load(listingId) }, enabled = !state.listingLookupLoading) { Text("Retry booking check") }
            } else if (state.existingBooking != null) {
                val existing = state.existingBooking!!
                if (SiteVisitUiRules.isPendingPayment(existing)) {
                    PendingPaymentResumeContent(
                        booking = existing,
                        busy = state.submitting || state.checkoutInProgress,
                        error = state.error,
                        message = state.message,
                        termsAccepted = termsAccepted,
                        onTermsAccepted = { termsAccepted = it },
                        onTermsClick = { showTerms = true },
                        onPay = { SiteVisitUiRules.paymentBookingId(existing)?.let(viewModel::createOrder) }
                    )
                } else if (SiteVisitUiRules.shouldOpenStatus(existing)) {
                    ExistingBookingStatusContent(existing, onViewStatus)
                }
            } else {
                Text("Listing #$listingId", style = MaterialTheme.typography.titleMedium)
                Text("Current Site Visit fee: ${state.feeRupees?.let { "₹$it" } ?: "Loading…"}")
                OutlinedTextField(
                    value = date,
                    onValueChange = {},
                    readOnly = true,
                    label = { Text("Preferred date (YYYY-MM-DD)") },
                    trailingIcon = {
                        IconButton(onClick = { showDatePicker = true }) {
                            Icon(Icons.Filled.CalendarMonth, contentDescription = "Choose preferred date")
                        }
                    },
                    modifier = Modifier.fillMaxWidth().clickable { showDatePicker = true },
                    singleLine = true
                )
                if (date.isBlank()) Text("Choose a preferred date.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                else if (dateTimeError?.contains("date", ignoreCase = true) == true) Text(dateTimeError!!, color = MaterialTheme.colorScheme.error)
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(
                        text = "Preferred Time",
                        style = MaterialTheme.typography.titleSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        TimeDropdown(
                            label = "Hour",
                            icon = Icons.Filled.AccessTime,
                            value = hour,
                            options = availableHours(date),
                            modifier = Modifier.weight(1f),
                            onSelected = { hour = it }
                        )
                        TimeDropdown(
                            label = "Minute",
                            icon = null,
                            value = minute,
                            options = availableMinutes(date, hour),
                            modifier = Modifier.weight(1f),
                            onSelected = { minute = it }
                        )
                    }
                }
                if (hour == null || minute == null) Text("Choose both an hour and minute.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                else if (dateTimeError != null) Text(dateTimeError, color = MaterialTheme.colorScheme.error)
            }
            if (showDatePicker) {
                val today = LocalDate.now()
                val selectedMillis = runCatching { LocalDate.parse(date).atStartOfDay(ZoneOffset.UTC).toInstant().toEpochMilli() }.getOrNull()
                val pickerState = rememberDatePickerState(
                    initialSelectedDateMillis = selectedMillis,
                    selectableDates = object : androidx.compose.material3.SelectableDates {
                        override fun isSelectableDate(utcTimeMillis: Long): Boolean =
                            !Instant.ofEpochMilli(utcTimeMillis).atZone(ZoneOffset.UTC).toLocalDate().isBefore(today)
                        override fun isSelectableYear(year: Int): Boolean = year >= today.year
                    }
                )
                DatePickerDialog(
                    onDismissRequest = { showDatePicker = false },
                    confirmButton = {
                        TextButton(onClick = {
                            pickerState.selectedDateMillis?.let { millis ->
                                date = SiteVisitBookingTime.formatDate(Instant.ofEpochMilli(millis).atZone(ZoneOffset.UTC).toLocalDate())
                                val selected = LocalDate.parse(date)
                                val now = LocalTime.now()
                                val chosenTime = hour?.let { h -> minute?.let { m -> SiteVisitBookingTime.timeFor(h, m) } }
                                if (chosenTime != null && !SiteVisitBookingTime.isTimeAllowed(selected, chosenTime, LocalDate.now(), now)) {
                                    hour = null
                                    minute = null
                                }
                            }
                            showDatePicker = false
                        }) { Text("OK") }
                    },
                    dismissButton = { TextButton(onClick = { showDatePicker = false }) { Text("Cancel") } }
                ) {
                    DatePicker(state = pickerState)
                }
            }
            if (listingId > 0 && state.booking == null && state.existingBooking == null && state.listingLookupComplete && state.listingLookupError == null) {
                OutlinedTextField(visitors, { visitors = it.filter { ch -> ch.isDigit() }.take(2) }, label = { Text("Number of visitors (1–20)") }, modifier = Modifier.fillMaxWidth(), singleLine = true, isError = (visitors.toIntOrNull() ?: 0) !in 1..20)
                if ((visitors.toIntOrNull() ?: 0) !in 1..20) Text("Enter between 1 and 20 visitors.", color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                OutlinedTextField(address, { address = it.take(1000) }, label = { Text("Pickup address") }, modifier = Modifier.fillMaxWidth(), minLines = 2, isError = address.trim().length !in 10..1000)
                if (address.trim().length !in 10..1000) Text("Enter a pickup address between 10 and 1000 characters.", color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                OutlinedTextField(message, { message = it.take(2000) }, label = { Text("Additional message (optional)") }, modifier = Modifier.fillMaxWidth(), minLines = 2)
                Button(
                    onClick = { viewModel.submit(listingId, date, "${hour}:${minute}", visitors, address, message) },
                    enabled = !state.submitting && formCanSubmit,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(if (state.submitting) "Please wait…" else "Submit Site Visit Request")
                }
                if (!formCanSubmit) Text("Complete the required fields above to submit your request.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            if (listingId > 0 && state.booking == null && state.existingBooking == null) state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            Spacer(Modifier.height(12.dp))
        }
    }

    if (showTerms) {
        AlertDialog(
            onDismissRequest = { showTerms = false },
            title = { Text("Site Visit Payment Terms") },
            text = {
                Text("The fee shown in the booking summary is processed through Razorpay. MyBrokerr confirms payment only after server-side verification. When the backend opens a refund case after cancellation, Accounting reviews and processes the refund manually; submitting refund details does not guarantee an automatic refund.")
            },
            confirmButton = { TextButton(onClick = { showTerms = false }) { Text("Close") } }
        )
    }

    cancellationTarget?.let { booking ->
        AlertDialog(
            onDismissRequest = { if (!state.canceling) cancellationTarget = null },
            title = { Text("Cancel Site Visit") },
            text = {
                val requiresRefundUpi = SiteVisitUiRules.requiresRefundUpiBeforeCancellation(booking)
                val validReason = cancellationReason.trim().length in 3..500
                val validUpi = !requiresRefundUpi || SiteVisitUiRules.isValidUpiId(cancellationUpiId)
                Column(
                    Modifier.verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text("Listing #${booking.listingId} • ${SiteVisitUiRules.displayDate(booking.visitDate)} at ${SiteVisitUiRules.displayTime(booking.visitTime)}")
                    Text(
                        if (requiresRefundUpi)
                            "Cancelling a paid visit opens a refund case first. Enter your UPI ID so it can be sent to Accounting for manual review. Submitting details does not guarantee an automatic refund."
                        else
                            "This booking has no successful Site Visit payment, so cancellation will not open a refund case."
                    )
                    OutlinedTextField(
                        value = cancellationUpiId,
                        onValueChange = { cancellationUpiId = it.take(120) },
                        label = { Text("UPI ID${if (requiresRefundUpi) "" else " (optional)"}") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        isError = cancellationValidationAttempted && requiresRefundUpi && !validUpi
                    )
                    if (cancellationValidationAttempted && requiresRefundUpi && !validUpi) {
                        Text("Enter a valid UPI ID, for example name@bank.", color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                    }
                    OutlinedTextField(
                        value = cancellationReason,
                        onValueChange = { cancellationReason = it.take(500) },
                        label = { Text("Cancellation reason") },
                        supportingText = { Text("Required") },
                        isError = cancellationValidationAttempted && !validReason,
                        minLines = 2
                    )
                    if (cancellationValidationAttempted && !validReason) {
                        Text("Enter a cancellation reason between 3 and 500 characters.", color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                    }
                    state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                }
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        cancellationValidationAttempted = true
                        if (cancellationReason.trim().length in 3..500 &&
                            (!SiteVisitUiRules.requiresRefundUpiBeforeCancellation(booking) || SiteVisitUiRules.isValidUpiId(cancellationUpiId))) {
                            viewModel.cancelBooking(booking, cancellationReason, cancellationUpiId)
                        }
                    },
                    enabled = !state.canceling
                ) { Text(if (state.canceling) "Submitting…" else "Submit Cancellation") }
            },
            dismissButton = { TextButton(onClick = { if (!state.canceling) cancellationTarget = null }) { Text("Back / Keep Booking") } }
        )
    }
}

@Composable
private fun TimeDropdown(
    label: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector?,
    value: String?,
    options: List<String>,
    modifier: Modifier = Modifier,
    onSelected: (String) -> Unit
) {
    var expanded by remember { mutableStateOf(false) }
    Box(modifier) {
        OutlinedTextField(
            value = value ?: "",
            onValueChange = {},
            readOnly = true,
            label = { Text(label) },
            placeholder = { Text("--") },
            trailingIcon = {
                if (icon != null) Icon(icon, contentDescription = null)
                else Icon(Icons.Filled.ArrowDropDown, contentDescription = "Choose $label")
            },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )
        Box(Modifier.fillMaxWidth().height(56.dp).clickable { expanded = true })
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEach { option ->
                DropdownMenuItem(text = { Text(option) }, onClick = { onSelected(option); expanded = false })
            }
        }
    }
}

private fun availableHours(dateText: String): List<String> {
    val selected = runCatching { LocalDate.parse(dateText) }.getOrNull() ?: return SiteVisitBookingTime.hours
    val today = LocalDate.now()
    if (selected != today) return SiteVisitBookingTime.hours
    val now = LocalTime.now()
    val firstHour = maxOf(9, now.hour)
    return SiteVisitBookingTime.hours.filter { it.toInt() >= firstHour }
}

private fun availableMinutes(dateText: String, hour: String?): List<String> {
    val all = SiteVisitBookingTime.minutes
    val selected = runCatching { LocalDate.parse(dateText) }.getOrNull() ?: return all
    val today = LocalDate.now()
    if (selected != today || hour == null || hour.toIntOrNull() != LocalTime.now().hour) return all
    return all.filter { it.toInt() > LocalTime.now().minute }
}

@Composable
private fun BookingSummaryContent(
    booking: SiteVisitBookingDto,
    termsAccepted: Boolean,
    busy: Boolean,
    error: String?,
    message: String?,
    onTermsClick: () -> Unit,
    onTermsAccepted: (Boolean) -> Unit,
    onPay: () -> Unit,
    onViewStatus: () -> Unit
) {
    Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Site Visit booking summary", style = MaterialTheme.typography.titleLarge)
            SiteVisitUiRules.summaryDetails(booking).forEach { (label, value) -> SummaryLine(label, value) }
            HorizontalDivider()
            Text("Refund", style = MaterialTheme.typography.titleSmall)
            Text(
                SiteVisitUiRules.refundStatusLabel(booking),
                style = MaterialTheme.typography.bodyMedium,
                color = if (booking.refund == null) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.primary
            )
            booking.refund?.takeIf { it.eligible }?.let { refund ->
                if (refund.eligibleAmountPaise > 0) Text("Eligible amount: ₹${"%.2f".format(refund.eligibleAmountPaise / 100.0)}")
                refund.actualRefundedAmountPaise?.let { Text("Actual refund: ₹${"%.2f".format(it / 100.0)}") }
            }
            androidx.compose.foundation.layout.Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(checked = termsAccepted, onCheckedChange = onTermsAccepted)
                Text("I have read and accept the payment terms.", modifier = Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium)
            }
            TextButton(onClick = onTermsClick) { Text("Read Terms & Conditions") }
            if (error != null) Text(error, color = MaterialTheme.colorScheme.error)
            if (message != null) Text(message, color = MaterialTheme.colorScheme.primary)
            val paid = booking.paymentStatus == "success"
            if (paid) {
                Text("Payment verified by MyBrokerr.", color = MaterialTheme.colorScheme.primary)
                Button(onClick = onViewStatus, modifier = Modifier.fillMaxWidth()) { Text("View Site Visit Status") }
            } else {
                Button(
                    onClick = onPay,
                    enabled = SiteVisitUiRules.isPaymentEnabled(booking, termsAccepted, busy),
                    modifier = Modifier.fillMaxWidth()
                ) { Text(if (busy) "Please wait…" else "Continue to Payment") }
                if (booking.bookingStatus != "pending_payment") {
                    Text("Payment is not available for this booking status.", style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
}

@Composable
private fun PendingPaymentResumeContent(
    booking: SiteVisitBookingDto,
    busy: Boolean,
    error: String?,
    message: String?,
    termsAccepted: Boolean,
    onTermsAccepted: (Boolean) -> Unit,
    onTermsClick: () -> Unit,
    onPay: () -> Unit
) {
    Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.tertiaryContainer)) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Pending Payment", style = MaterialTheme.typography.titleLarge)
            Text("You already have a Site Visit request for this Sell Land listing. Continue its payment; no new booking will be created.")
            SiteVisitUiRules.summaryDetails(booking).forEach { (label, value) -> SummaryLine(label, value) }
            Text("Visit: ${SiteVisitUiRules.displayDate(booking.visitDate)} • ${SiteVisitUiRules.displayTime(booking.visitTime)}")
            HorizontalDivider()
            androidx.compose.foundation.layout.Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(checked = termsAccepted, onCheckedChange = onTermsAccepted)
                Text("I have read and accept the payment terms.", modifier = Modifier.weight(1f))
            }
            TextButton(onClick = onTermsClick) { Text("Read Terms & Conditions") }
            error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            message?.let { Text(it, color = MaterialTheme.colorScheme.primary) }
            Button(
                onClick = onPay,
                enabled = SiteVisitUiRules.isPaymentEnabled(booking, termsAccepted, busy),
                modifier = Modifier.fillMaxWidth()
            ) { Text(if (busy) "Please wait…" else SiteVisitUiRules.paymentActionLabel(booking)) }
        }
    }
}

@Composable
private fun ExistingBookingStatusContent(booking: SiteVisitBookingDto, onViewStatus: () -> Unit) {
    Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Existing Site Visit", style = MaterialTheme.typography.titleLarge)
            Text("A booking already exists for this listing. No additional booking will be created.")
            SiteVisitUiRules.summaryDetails(booking).forEach { (label, value) -> SummaryLine(label, value) }
            StatusBadge(booking.bookingStatus)
            Button(onClick = onViewStatus, modifier = Modifier.fillMaxWidth()) { Text("View Site Visit Status") }
        }
    }
}

@Composable
private fun SummaryLine(label: String, value: String) {
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, style = MaterialTheme.typography.bodyLarge)
    }
}

@Composable
private fun SiteVisitStatusCard(
    booking: SiteVisitBookingDto,
    onCancel: () -> Unit,
    onResubmit: (SiteVisitBookingDto, String, String, String, String, String) -> Unit,
    onSubmitRefund: (SiteVisitBookingDto, String) -> Unit,
    busy: Boolean,
    highlighted: Boolean = false
) {
    var correctedDate by remember(booking.id, booking.bookingStatus) { mutableStateOf(booking.visitDate) }
    var correctedTime by remember(booking.id, booking.bookingStatus) { mutableStateOf(booking.visitTime.take(5)) }
    var correctedVisitors by remember(booking.id, booking.bookingStatus) { mutableStateOf(booking.visitorCount.toString()) }
    var correctedAddress by remember(booking.id, booking.bookingStatus) { mutableStateOf(booking.pickupAddress) }
    var correctedMessage by remember(booking.id, booking.bookingStatus) { mutableStateOf(booking.message.orEmpty()) }
    var refundUpiId by remember(booking.id, booking.refund?.status) { mutableStateOf("") }
    Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = if (highlighted) MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.surface), elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Text("Site Visit Booking ID: ${booking.id}", style = MaterialTheme.typography.titleMedium)
                    Text(booking.propertyName, style = MaterialTheme.typography.bodyMedium)
                }
                StatusBadge(booking.bookingStatus)
            }
            Text("Sell Land", style = MaterialTheme.typography.titleSmall)
            SummaryLine("Listing ID", booking.listingId.toString())
            Text("Site Visit", style = MaterialTheme.typography.titleSmall)
            HorizontalDivider()
            androidx.compose.foundation.layout.Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(20.dp)) {
                Column(Modifier.weight(1f)) {
                    Text("Visit Date", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(SiteVisitUiRules.displayDate(booking.visitDate), style = MaterialTheme.typography.titleMedium)
                }
                Column(Modifier.weight(1f)) {
                    Text("Visit Time", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(SiteVisitUiRules.displayTime(booking.visitTime), style = MaterialTheme.typography.titleMedium)
                }
            }
            Text("${booking.visitorCount} visitor(s) • Fee ₹${booking.feeRupees}")
            if (booking.bookingStatus == "correction_required") {
                Text("Admin requested a correction", style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.error)
                Text(booking.correctionReason ?: "The admin did not provide a reason.")
                OutlinedTextField(correctedDate, { correctedDate = it }, label = { Text("Visit date (YYYY-MM-DD)") }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(correctedTime, { correctedTime = it }, label = { Text("Visit time (HH:MM)") }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(correctedVisitors, { correctedVisitors = it.filter(Char::isDigit).take(2) }, label = { Text("Visitor count") }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(correctedAddress, { correctedAddress = it.take(1000) }, label = { Text("Pickup address") }, modifier = Modifier.fillMaxWidth(), minLines = 2)
                OutlinedTextField(correctedMessage, { correctedMessage = it.take(2000) }, label = { Text("Message (optional)") }, modifier = Modifier.fillMaxWidth())
                Button(
                    enabled = !correctedDate.isBlank() && !correctedTime.isBlank() && correctedVisitors.toIntOrNull()?.let { it in 1..20 } == true && correctedAddress.trim().length in 10..1000,
                    onClick = { onResubmit(booking, correctedDate.trim(), correctedTime.trim(), correctedVisitors, correctedAddress, correctedMessage) },
                    modifier = Modifier.fillMaxWidth()
                ) { Text("Resubmit corrected details") }
            }
            if (booking.bookingStatus == "cancelled") {
                Text("Cancelled by: ${booking.cancelledByRole?.replace('_', ' ')?.replaceFirstChar { it.uppercase() } ?: "Unknown"}", style = MaterialTheme.typography.titleSmall)
                booking.cancellationReason?.let { Text("Cancellation reason: $it") }
            }
            Text("Refund", style = MaterialTheme.typography.titleSmall)
            Text(
                SiteVisitUiRules.refundStatusLabel(booking),
                style = MaterialTheme.typography.bodyMedium,
                color = if (booking.refund == null) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.primary
            )
            booking.refund?.let { refund ->
                if (refund.eligibleAmountPaise > 0) Text("Eligible amount: ₹${"%.2f".format(refund.eligibleAmountPaise / 100.0)}")
                refund.actualRefundedAmountPaise?.let { Text("Actual refund: ₹${"%.2f".format(it / 100.0)}") }
                refund.transactionReference?.let { Text("UPI transaction reference: $it") }
                if (refund.status == "pending_details") {
                    val validRefundUpi = SiteVisitUiRules.isValidUpiId(refundUpiId)
                    OutlinedTextField(
                        value = refundUpiId,
                        onValueChange = { refundUpiId = it.take(120) },
                        label = { Text("Refund UPI ID") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        isError = refundUpiId.isNotBlank() && !validRefundUpi
                    )
                    if (refundUpiId.isNotBlank() && !validRefundUpi) {
                        Text("Enter a valid UPI ID, for example name@bank.", color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                    }
                    Button(enabled = !busy && validRefundUpi, onClick = { onSubmitRefund(booking, refundUpiId.trim()) }) {
                        Text(if (busy) "Submitting…" else "Submit refund UPI ID")
                    }
                }
            }
            booking.workflowHistory.forEach { event ->
                Text("${event.eventType.replace('_', ' ')} • ${event.actorRole} • ${event.createdAt}", style = MaterialTheme.typography.bodySmall)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                Text("Payment:", style = MaterialTheme.typography.labelLarge)
                StatusBadge(booking.paymentStatus)
            }
            if (booking.bookingStatus !in setOf("cancelled", "refund_pending", "refunded", "refund_failed")) {
                val progress = SiteVisitUiRules.progressIndex(booking.bookingStatus)
                if (progress >= 0) {
                    LinearProgressIndicator(progress = { SiteVisitUiRules.progressFraction(booking.bookingStatus) }, modifier = Modifier.fillMaxWidth())
                    Text("${SiteVisitUiRules.progressLabels()[progress]} • ${statusDescription(booking.bookingStatus)}", style = MaterialTheme.typography.bodySmall)
                } else Text(statusDescription(booking.bookingStatus), style = MaterialTheme.typography.bodySmall)
            } else {
                Text(statusDescription(booking.bookingStatus), style = MaterialTheme.typography.bodySmall)
            }
            booking.completionCode?.let { activeCode ->
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    color = MaterialTheme.colorScheme.secondaryContainer,
                    contentColor = MaterialTheme.colorScheme.onSecondaryContainer,
                    shape = RoundedCornerShape(14.dp)
                ) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                        Text("Share this completion code with your Field Officer", style = MaterialTheme.typography.titleSmall)
                        Text(activeCode, style = MaterialTheme.typography.headlineMedium, fontWeight = androidx.compose.ui.text.font.FontWeight.Bold)
                        Text("Only share it with the Field Officer assigned to this booking.", style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
            if (booking.completionCode == null && booking.bookingStatus == "in_progress") {
                Text(
                    "Waiting for the Field Officer to initiate completion. Refresh My Site Visits to check for your code.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            if (SiteVisitUiRules.canCancel(booking)) {
                TextButton(onClick = onCancel) { Text("Cancel Site Visit") }
            }
        }
    }
}

@Composable
private fun StatusBadge(status: String) {
    val normalized = status.lowercase()
    val background = when (normalized) {
        "completed", "success", "refunded" -> MaterialTheme.colorScheme.tertiaryContainer
        "cancelled", "failed", "refund_failed" -> MaterialTheme.colorScheme.errorContainer
        "in_progress", "scheduled", "assigned", "correction_required", "refund_pending" -> MaterialTheme.colorScheme.secondaryContainer
        else -> MaterialTheme.colorScheme.primaryContainer
    }
    val foreground = when (normalized) {
        "completed", "success", "refunded" -> MaterialTheme.colorScheme.onTertiaryContainer
        "cancelled", "failed", "refund_failed" -> MaterialTheme.colorScheme.onErrorContainer
        "in_progress", "scheduled", "assigned", "correction_required", "refund_pending" -> MaterialTheme.colorScheme.onSecondaryContainer
        else -> MaterialTheme.colorScheme.onPrimaryContainer
    }
    Surface(color = background, contentColor = foreground, shape = RoundedCornerShape(50)) {
        Text(status.replace('_', ' ').replaceFirstChar { it.uppercase() }, Modifier.padding(horizontal = 10.dp, vertical = 5.dp), style = MaterialTheme.typography.labelMedium)
    }
}

private fun statusDescription(status: String): String = when (status) {
    "pending_payment" -> "Complete payment to continue your request."
    "pending" -> "Your paid request is awaiting assignment."
    "assigned" -> "A Field Officer has been assigned to your visit."
    "scheduled" -> "Your visit is scheduled."
    "in_progress" -> "Your Site Visit is in progress."
    "completed" -> "Your Site Visit is complete."
    "correction_required" -> "An admin requested changes. Review the reason and resubmit the requested booking details."
    "cancelled" -> "The Site Visit was cancelled. Review the recorded cancellation reason and any refund request status."
    "refund_pending" -> "Refund is pending according to the server status."
    "refunded" -> "The server reports that this booking was refunded."
    "refund_failed" -> "The server reports a refund failure. Contact support for assistance."
    else -> "Latest booking status from MyBrokerr."
}

