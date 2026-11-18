package com.example.mybroker_admin.feature.superadmin.listings.screen

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.background
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Button
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import android.util.Log
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import com.example.mybroker_admin.BuildConfig
import com.example.mybroker_admin.core.session.SessionManager
import com.example.mybroker_admin.feature.admin.listings.BookedListingDetailUi
import com.example.mybroker_admin.feature.admin.listings.BookedListingDetailViewModel
import com.example.mybroker_admin.feature.admin.listings.PropertyBookingCancellationUiPolicy
import com.example.mybroker_admin.feature.admin.listings.PropertyBookingCancellationUiState
import com.example.mybroker_admin.feature.admin.listings.presentation.components.SectionCard
import com.example.mybroker_admin.feature.admin.listings.BookingDocumentUi
import com.example.mybroker_admin.data.remote.PrivatePdfViewer
import com.example.mybroker_admin.feature.superadmin.listings.viewmodel.SuperAdminListingDetailViewModel
import coil.compose.AsyncImage
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.LocalTime
import java.time.format.DateTimeFormatter

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SuperAdminListingDetailScreen(
    navController: NavHostController,
    listingId: Int
) {
    val vm: SuperAdminListingDetailViewModel = viewModel()
    val state by vm.state.collectAsState()
    val detail by vm.detail.collectAsState()
    val bookedDetail by vm.bookedDetail.collectAsState()
    val bookingError by vm.bookingError.collectAsState()
    val cancellationVm: BookedListingDetailViewModel = viewModel()
    val cancellationState by cancellationVm.state.collectAsState()
    val role = SessionManager.currentUserRole
    val isSuperAdmin = SessionManager.accessToken != null && PropertyBookingCancellationUiPolicy.isSuperAdmin(role)
    val cancellationUi = PropertyBookingCancellationUiState(
        role = role.takeIf { SessionManager.accessToken != null },
        readOnly = false,
        previewLoading = cancellationState.isLoadingCancellationPreview,
        previewError = cancellationState.cancellationPreviewError,
        preview = cancellationState.cancellationPreview,
        isSubmitting = cancellationState.isCancellingBooking
    )
    val context = LocalContext.current
    val documentScope = rememberCoroutineScope()

    androidx.compose.runtime.LaunchedEffect(listingId) {
        vm.loadDetail(listingId)
    }
    LaunchedEffect(bookedDetail?.bookingId, isSuperAdmin) {
        if (isSuperAdmin) bookedDetail?.bookingId?.let(cancellationVm::loadCancellationPreview)
    }
    LaunchedEffect(cancellationState.cancellationCompleted) {
        if (cancellationState.cancellationCompleted) vm.loadDetail(listingId)
    }
    LaunchedEffect(
        role,
        isSuperAdmin,
        listingId,
        bookedDetail?.bookingId,
        bookedDetail?.bookingStatus,
        cancellationState.isLoadingCancellationPreview,
        cancellationState.cancellationPreviewError,
        cancellationState.cancellationPreview?.can_cancel
    ) {
        if (BuildConfig.DEBUG) {
            Log.d(
                "BookingCancelUi",
                "screen=SuperAdminListingDetail role_raw=$role " +
                    "role_normalized=${PropertyBookingCancellationUiPolicy.normalizeRole(role)} " +
                    "is_super_admin=$isSuperAdmin listing_id=$listingId " +
                    "booking_id=${bookedDetail?.bookingId ?: cancellationState.cancellationPreview?.booking_id} " +
                    "booking_status=${bookedDetail?.bookingStatus ?: cancellationState.cancellationPreview?.booking_status} " +
                    "preview_loading=${cancellationState.isLoadingCancellationPreview} " +
                    "preview_failed=${cancellationState.cancellationPreviewError != null} " +
                    "can_cancel=${cancellationState.cancellationPreview?.can_cancel} " +
                    "section_visible=${cancellationUi.actionsVisible}"
            )
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Property Details") },
                navigationIcon = {
                    androidx.compose.material3.TextButton(onClick = { navController.popBackStack() }) {
                        Text("Back")
                    }
                }
            )
        }
    ) { padding ->
        if (state.isLoading) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(16.dp)
            ) {
                SuperAdminPropertyBookingActions(
                    listingId, null, cancellationState, cancellationUi,
                    { id -> cancellationVm.loadCancellationPreview(id) },
                    { id, choice, amount, reason -> cancellationVm.cancelPropertyBooking(id, choice, amount, reason) }
                )
                CircularProgressIndicator()
            }
            return@Scaffold
        }

        if (!state.error.isNullOrBlank()) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(16.dp)
            ) {
                SuperAdminPropertyBookingActions(
                    listingId, null, cancellationState, cancellationUi,
                    { id -> cancellationVm.loadCancellationPreview(id) },
                    { id, choice, amount, reason -> cancellationVm.cancelPropertyBooking(id, choice, amount, reason) }
                )
                Text(text = state.error ?: "Failed to load detail", color = MaterialTheme.colorScheme.error)
            }
            return@Scaffold
        }

        if (detail == null) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(16.dp)
            ) {
                SuperAdminPropertyBookingActions(
                    listingId, null, cancellationState, cancellationUi,
                    { id -> cancellationVm.loadCancellationPreview(id) },
                    { id, choice, amount, reason -> cancellationVm.cancelPropertyBooking(id, choice, amount, reason) }
                )
                Text("Listing not found")
            }
            return@Scaffold
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
                .verticalScroll(rememberScrollState())
        ) {
            SuperAdminPropertyBookingActions(
                listingId, bookedDetail, cancellationState, cancellationUi,
                { id -> cancellationVm.loadCancellationPreview(id) },
                { id, choice, amount, reason -> cancellationVm.cancelPropertyBooking(id, choice, amount, reason) }
            )
            Spacer(Modifier.height(12.dp))
            SectionCard(title = "Status & Review") {
                Text("Current Status: ${detail!!.status}")
                if (!detail!!.reviewedAt.isNullOrBlank()) {
                    Text("Reviewed At: ${formatDateTime(detail!!.reviewedAt)}")
                }
                if (detail!!.reviewedById != null) {
                    Text("Reviewed By ID: ${detail!!.reviewedById}")
                }
                if (!detail!!.rejectionReason.isNullOrBlank()) {
                    Text("Rejection Reason: ${detail!!.rejectionReason}")
                }
            }

            Spacer(Modifier.height(12.dp))

            SectionCard(title = "Submission & Payment") {
                if (!detail!!.submittedAt.isNullOrBlank()) {
                    Text("Submitted At: ${formatDateTime(detail!!.submittedAt)}")
                }
                if (!detail!!.paymentStatus.isNullOrBlank()) {
                    Text("Payment Status: ${detail!!.paymentStatus}")
                }
                if (!detail!!.paymentPaidAt.isNullOrBlank()) {
                    Text("Payment Paid At: ${formatDateTime(detail!!.paymentPaidAt)}")
                }
                if (!detail!!.paymentAmount.isNullOrBlank()) {
                    Text("Payment Amount: ${detail!!.paymentAmount}")
                }
            }

            Spacer(Modifier.height(12.dp))

            if (!detail!!.cancellationReason.isNullOrBlank()
                || !detail!!.refundUpiId.isNullOrBlank()
                || !detail!!.refundAmount.isNullOrBlank()
                || !detail!!.refundTxnId.isNullOrBlank()
                || !detail!!.refundCompletedAt.isNullOrBlank()
            ) {
                SectionCard(title = "Refund Details") {
                    if (!detail!!.cancellationReason.isNullOrBlank()) {
                        Text("Cancellation Reason: ${detail!!.cancellationReason}")
                    }
                    if (!detail!!.refundUpiId.isNullOrBlank()) {
                        Text("Refund UPI: ${detail!!.refundUpiId}")
                    }
                    if (!detail!!.refundAmount.isNullOrBlank()) {
                        Text("Refund Amount: ${detail!!.refundAmount}")
                    }
                    if (!detail!!.refundTxnId.isNullOrBlank()) {
                        Text("Refund Txn ID: ${detail!!.refundTxnId}")
                    }
                    if (!detail!!.refundCompletedAt.isNullOrBlank()) {
                        Text("Refund Completed At: ${formatDateTime(detail!!.refundCompletedAt)}")
                    }
                }
                Spacer(Modifier.height(12.dp))
            }

            SectionCard(title = "Handled By") {
                if (!detail!!.adminHandlerName.isNullOrBlank()) {
                    Text("Admin: ${detail!!.adminHandlerName}")
                    if (!detail!!.adminHandlerMobile.isNullOrBlank()) {
                        Text("Admin Mobile: ${detail!!.adminHandlerMobile}")
                    }
                } else {
                    Text("Admin: Not assigned")
                }

                Spacer(Modifier.height(6.dp))

                if (!detail!!.fieldOfficerName.isNullOrBlank()) {
                    Text("Field Officer: ${detail!!.fieldOfficerName}")
                    if (!detail!!.fieldOfficerMobile.isNullOrBlank()) {
                        Text("Field Officer Mobile: ${detail!!.fieldOfficerMobile}")
                    }
                } else {
                    Text("Field Officer: Not assigned")
                }
            }

            Spacer(Modifier.height(12.dp))

            if (bookingError != null) {
                SectionCard(title = "Booking Details") {
                    Text(text = bookingError ?: "Failed to load booking details", color = MaterialTheme.colorScheme.error)
                }
                Spacer(Modifier.height(12.dp))
            }

            if (bookedDetail != null) {
                SectionCard(title = "Booking Summary") {
                    Text("Booking Reference: ${bookedDetail!!.bookingId}")
                    Text("Booked At: ${formatDateTime(bookedDetail!!.bookedAt)}")
                    Text("Booking Status: ${bookedDetail!!.bookingStatus}")
                    Text("Deal Price: ${bookedDetail!!.land.dealPrice ?: "-"}")
                }

                if (bookedDetail!!.bookingStatus == "Booking Cancelled") {
                    Spacer(Modifier.height(12.dp))
                    SectionCard(title = "Booking Cancellation") {
                        Text("Booking Reference: ${bookedDetail!!.bookingId}")
                        Text("Cancellation Reason: ${bookedDetail!!.cancellationReason ?: "Unavailable"}")
                        Text("Refund Decision: ${bookedDetail!!.refundDecision ?: "Unavailable"}")
                        Text("Refund Status: ${bookedDetail!!.refundStatus ?: "Unavailable"}")
                        Text(
                            "Refund Amount: ${if (bookedDetail!!.refundDecision == "NO_REFUND") "No Refund" else bookedDetail!!.actualRefundedAmount ?: bookedDetail!!.approvedRefundAmount ?: "Unavailable"}"
                        )
                        bookedDetail!!.refundReference?.let { Text("Refund Reference: $it") }
                        bookedDetail!!.cancelledAt?.let { Text("Cancelled At: ${formatDateTime(it)}") }
                    }
                }

                Spacer(Modifier.height(12.dp))

                SectionCard(title = "Buyer Details") {
                    Text("Name: ${bookedDetail!!.buyer.name}")
                    Text("Mobile: ${bookedDetail!!.buyer.mobile ?: "-"}")
                    DocumentList(
                        title = "Buyer Documents",
                        documents = bookedDetail!!.buyer.documents,
                        onViewDocument = { url -> PrivatePdfViewer.open(context, documentScope, url) }
                    )
                }

                Spacer(Modifier.height(12.dp))

                SectionCard(title = "Booking Payment") {
                    Text("Token Amount: ${bookedDetail!!.payment.tokenAmount ?: "-"}")
                    Text("Remaining Amount: ${bookedDetail!!.payment.remainingAmount ?: "-"}")
                    Text("Payment Status: ${bookedDetail!!.payment.status ?: "-"}")
                }

                Spacer(Modifier.height(12.dp))

                SectionCard(title = "Field Officer Assignment") {
                    Text("Name: ${bookedDetail!!.fieldOfficer?.name ?: "-"}")
                    Text("Mobile: ${bookedDetail!!.fieldOfficer?.mobile ?: "-"}")
                }

                Spacer(Modifier.height(12.dp))

                SectionCard(title = "Registry & Proofs") {
                    val reg = bookedDetail!!.registry
                    Text("Registry Date: ${formatDate(reg?.date)}")
                    Text("Registry Time: ${formatTime(reg?.time)}")
                    Text("Registry Location: ${reg?.location ?: "-"}")
                    Text("Registry Status: ${reg?.status ?: "-"}")
                    DocumentList(
                        title = "Registry Proofs",
                        documents = reg?.proofs ?: emptyList(),
                        onViewDocument = { url -> PrivatePdfViewer.open(context, documentScope, url) }
                    )
                }

                Spacer(Modifier.height(12.dp))
            }

            SectionCard(title = "Seller Details") {
                Text("Name: ${detail!!.sellerName}")
                Text("Mobile: ${detail!!.sellerMobile}")
                Text("Seller Type: ${detail!!.ownershipType}")
                Text("Category: ${detail!!.sellerCategory}")
            }

            Spacer(Modifier.height(12.dp))

            SectionCard(title = "Land Photos") {
                if (detail!!.photos.isEmpty()) {
                    Text("No photos uploaded")
                } else {
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        items(detail!!.photos) { url ->
                            AsyncImage(
                                model = url,
                                contentDescription = "Land photo",
                                modifier = Modifier
                                    .width(140.dp)
                                    .height(90.dp)
                                    .background(Color(0xFFEFEFEF), RoundedCornerShape(10.dp)),
                                alignment = Alignment.Center
                            )
                        }
                    }
                }
            }

            Spacer(Modifier.height(12.dp))

            SectionCard(title = "Land Details") {
                Text("Title: ${detail!!.title}")
                Text("Type: ${detail!!.landType}")
                Text("Area: ${detail!!.area}")
                Text("City: ${detail!!.city}")
                Text("State: ${detail!!.state}")
                Text("Pincode: ${detail!!.pincode}")
            }

            Spacer(Modifier.height(12.dp))

            SectionCard(title = "Instagram Promotion") {
                Text(detail!!.instagramUrl ?: "No Instagram URL saved")
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = state.instagramInput,
                    onValueChange = vm::onInstagramInputChange,
                    label = { Text("Instagram URL") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !state.instagramSaving
                )
                Spacer(Modifier.height(8.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = { vm.saveInstagramUrl(listingId) }, enabled = !state.instagramSaving) {
                        Text(if (detail!!.instagramUrl.isNullOrBlank()) "Add" else "Update")
                    }
                    TextButton(
                        onClick = { vm.removeInstagramUrl(listingId) },
                        enabled = !state.instagramSaving && !detail!!.instagramUrl.isNullOrBlank()
                    ) { Text("Remove") }
                    if (state.instagramSaving) CircularProgressIndicator(modifier = Modifier.height(24.dp))
                }
                state.instagramMessage?.let { Text(it, color = MaterialTheme.colorScheme.primary) }
                state.instagramError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            }

            Spacer(Modifier.height(12.dp))

            SectionCard(title = "Pricing") {
                Text("Price Type: ${detail!!.priceType}")
                Text("Expected Price: ${detail!!.expectedPrice}")
                Text("Negotiable: ${if (detail!!.negotiable) "Yes" else "No"}")
            }

            Spacer(Modifier.height(12.dp))

            SectionCard(title = "Documents Uploaded") {
                if (detail!!.documents.isEmpty()) {
                    Text("No documents uploaded")
                } else {
                    detail!!.documents.forEach { doc ->
                        Text(
                            text = "✔ ${doc.name}",
                            modifier = Modifier.clickable {
                                PrivatePdfViewer.open(context, documentScope, doc.url)
                            },
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                }
            }

            Spacer(Modifier.height(12.dp))

            SectionCard(title = "Action Timeline") {
                TimelineItem("Submitted", detail!!.submittedAt)
                TimelineItem("Payment Paid", detail!!.paymentPaidAt)
                TimelineItem("Admin Reviewed", detail!!.reviewedAt)
                TimelineItem("Booked", bookedDetail?.bookedAt)
                TimelineItem(
                    "Registry Scheduled",
                    bookedDetail?.registry?.date?.let { date ->
                        val time = bookedDetail?.registry?.time
                        if (!time.isNullOrBlank()) "${date}T$time" else date
                    }
                )
                TimelineItem("Refund Completed", detail!!.refundCompletedAt)
            }
        }
    }
}

@Composable
private fun SuperAdminPropertyBookingActions(
    listingId: Int,
    booking: BookedListingDetailUi?,
    state: com.example.mybroker_admin.feature.admin.listings.BookedListingDetailState,
    cancellationUi: PropertyBookingCancellationUiState,
    onRetryPreview: (Int) -> Unit,
    onCancelBooking: (Int, String, Double, String) -> Unit
) {
    if (!cancellationUi.actionsVisible) return

    val preview = state.cancellationPreview?.takeIf {
        booking != null && it.booking_id == booking.bookingId && it.listing_id == listingId
    }
    val dialogOpen = remember { mutableStateOf(false) }
    val reason = remember { mutableStateOf("") }
    val decision = remember { mutableStateOf("REFUND") }
    val formError = remember { mutableStateOf<String?>(null) }
    val refundAmount = remember(preview?.captured_payment_amount) {
        mutableStateOf(preview?.captured_payment_amount?.toString().orEmpty())
    }
    val bookingId = booking?.bookingId ?: preview?.booking_id

    SectionCard(title = "SUPER ADMIN ACTIONS") {
        Text("Booking ID: ${bookingId?.toString() ?: "Loading booking details"}")
        Text("Listing ID: ${preview?.listing_id ?: booking?.listingId ?: listingId}")
        Text("Booking Status: ${preview?.booking_status ?: booking?.bookingStatus ?: "Unavailable"}")
        preview?.captured_payment_amount?.let { Text("Verified captured payment: ₹$it") }

        when {
            state.isLoadingCancellationPreview -> {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(modifier = Modifier.height(20.dp))
                    Text(" Checking cancellation eligibility")
                }
            }
            state.cancellationPreviewError != null ->
                Text(state.cancellationPreviewError, color = MaterialTheme.colorScheme.error)
            preview != null && !preview.can_cancel ->
                Text(
                    preview.blocking_reason ?: "This booking is not eligible for cancellation.",
                    color = MaterialTheme.colorScheme.error
                )
            bookingId == null -> Text("Waiting for booking details")
            preview?.can_cancel == true ->
                Text("This booking is eligible for cancellation.", color = MaterialTheme.colorScheme.primary)
        }

        if (state.cancellationPreviewError != null && bookingId != null) {
            TextButton(
                onClick = { onRetryPreview(bookingId) },
                enabled = !state.isLoadingCancellationPreview
            ) { Text("Retry Preview") }
        }

        Button(
            onClick = {
                formError.value = null
                reason.value = ""
                dialogOpen.value = true
            },
            modifier = Modifier.fillMaxWidth(),
            enabled = bookingId != null && !state.isCancellingBooking && preview?.can_cancel != false
        ) { Text("CANCEL PROPERTY BOOKING") }
    }

    if (dialogOpen.value) {
        AlertDialog(
            onDismissRequest = { if (!state.isCancellingBooking) dialogOpen.value = false },
            title = { Text("Cancel Property Booking") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Booking ID: ${bookingId ?: "Unavailable"} · Listing ID: $listingId")
                    Text("Captured payment: ${preview?.captured_payment_amount?.let { "₹$it" } ?: "Unavailable"}")
                    if (decision.value == "REFUND") {
                        Text("Default refundable amount: ${preview?.captured_payment_amount?.let { "₹$it" } ?: "Unavailable"}")
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(onClick = { decision.value = "REFUND" }) {
                            Text(if (decision.value == "REFUND") "✓ Refund" else "Refund")
                        }
                        OutlinedButton(onClick = { decision.value = "NO_REFUND" }) {
                            Text(if (decision.value == "NO_REFUND") "✓ No Refund" else "No Refund")
                        }
                    }
                    if (decision.value == "REFUND") {
                        OutlinedTextField(
                            value = refundAmount.value,
                            onValueChange = { refundAmount.value = it },
                            label = { Text("Refund amount") },
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                    OutlinedTextField(
                        value = reason.value,
                        onValueChange = { reason.value = it },
                        label = { Text("Reason (required)") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    formError.value?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                    state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                }
            },
            confirmButton = {
                TextButton(
                    enabled = !state.isCancellingBooking,
                    onClick = {
                        val amount = PropertyBookingCancellationUiPolicy.amountForSubmission(
                            decision.value,
                            refundAmount.value,
                            preview?.captured_payment_amount
                        )
                        when {
                            reason.value.trim().length < 5 -> formError.value = "Enter a cancellation reason (at least 5 characters)."
                            bookingId == null -> formError.value = "Booking details are not available yet."
                            amount == null -> formError.value = "Enter a valid refund amount within the captured payment."
                            else -> {
                                formError.value = null
                                onCancelBooking(bookingId, decision.value, amount, reason.value.trim())
                                dialogOpen.value = false
                            }
                        }
                    }
                ) { Text(if (state.isCancellingBooking) "Submitting…" else "Confirm Cancellation") }
            },
            dismissButton = {
                TextButton(
                    enabled = !state.isCancellingBooking,
                    onClick = { dialogOpen.value = false }
                ) { Text("Back") }
            }
        )
    }
}

@Composable
private fun DocumentList(
    title: String,
    documents: List<BookingDocumentUi>,
    onViewDocument: (String) -> Unit
) {
    Spacer(modifier = Modifier.height(6.dp))
    Text(text = title, style = MaterialTheme.typography.titleSmall)
    if (documents.isEmpty()) {
        Spacer(modifier = Modifier.height(6.dp))
        Text(text = "No documents uploaded", style = MaterialTheme.typography.bodySmall)
        return
    }
    Spacer(modifier = Modifier.height(6.dp))
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        documents.forEach { doc ->
            Text(
                text = doc.createdAt?.let { "${doc.name} • ${formatDateTime(it)}" } ?: doc.name,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.clickable { onViewDocument(doc.url) },
                color = MaterialTheme.colorScheme.primary
            )
        }
    }
}

@Composable
private fun TimelineItem(
    label: String,
    value: String?
) {
    if (value.isNullOrBlank()) return
    Text(text = "$label: ${formatDateTime(value)}")
}

private fun formatDate(value: String?): String {
    if (value.isNullOrBlank()) return "-"
    return try {
        val parsed = LocalDate.parse(value)
        parsed.format(DateTimeFormatter.ofPattern("dd-MMM-yyyy"))
    } catch (_: Exception) {
        value
    }
}

private fun formatTime(value: String?): String {
    if (value.isNullOrBlank()) return "-"
    return try {
        val parsed = LocalTime.parse(value)
        parsed.format(DateTimeFormatter.ofPattern("hh.mm a"))
    } catch (_: Exception) {
        value
    }
}

private fun formatDateTime(value: String?): String {
    if (value.isNullOrBlank()) return "-"
    return try {
        val parsed = LocalDateTime.parse(value)
        parsed.format(DateTimeFormatter.ofPattern("dd-MMM-yyyy, hh.mm a"))
    } catch (_: Exception) {
        try {
            val parsedDate = LocalDate.parse(value)
            parsedDate.format(DateTimeFormatter.ofPattern("dd-MMM-yyyy"))
        } catch (_: Exception) {
            value
        }
    }
}

