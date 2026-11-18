package com.example.mybroker_admin.feature.sitevisit

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.clickable
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
//import androidx.compose.foundation.layout.weight
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.ui.graphics.Color
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import android.util.Log
import androidx.compose.material3.LinearProgressIndicator
import com.example.mybroker_admin.BuildConfig
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.core.session.SessionManager
import java.math.BigDecimal
import java.io.IOException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import retrofit2.HttpException

@Composable
fun AdminSiteVisitsScreen(onOpenBooking: (Int) -> Unit, refreshKey: Long = 0L) {
    val api = ApiClient.siteVisitApi
    val scope = rememberCoroutineScope()
    var rows by remember { mutableStateOf<List<SiteVisitListItemDto>>(emptyList()) }
    var summary by remember { mutableStateOf<SiteVisitSummaryDto?>(null) }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var filter by remember { mutableStateOf("all") }
    fun refresh(status: String? = filter.takeUnless { it == "all" }) = scope.launch {
        loading = true
        error = null
        try {
            val firstPage = api.list(status = status)
            val allRows = firstPage.items.toMutableList()
            var nextSkip = firstPage.skip + firstPage.items.size
            while (nextSkip < firstPage.total && firstPage.items.isNotEmpty()) {
                val page = api.list(skip = nextSkip, limit = firstPage.limit, status = status)
                if (page.items.isEmpty()) break
                allRows += page.items
                nextSkip = page.skip + page.items.size
            }
            val summaryResult = api.summary()
            rows = sortSiteVisitBookings(allRows)
            summary = summaryResult
        }
        catch (e: Exception) { error = "Could not load Site Visit queue. Check access or connection." }
        finally { loading = false }
    }
    LaunchedEffect(refreshKey) { refresh() }

    val filters = listOf(
        "all" to "All", "pending" to "Pending", "correction_required" to "Correction Required",
        "assigned" to "Assigned", "scheduled" to "Scheduled", "in_progress" to "In Progress",
        "completed" to "Completed", "cancelled" to "Cancelled"
    )
    val summaryCounts = summary?.let {
        mapOf(
            "all" to it.totalPaid,
            "pending" to it.pending,
            "assigned" to it.assigned,
            "scheduled" to it.scheduled,
            "in_progress" to it.inProgress,
            "completed" to it.completed,
            "cancelled" to it.cancelled
        )
    }.orEmpty()

    Scaffold { inset ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(inset),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 18.dp, vertical = 14.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            item(key = "dashboard_header") {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Column {
                        Text("Paid Site Visits", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                        Text("Manage paid buyer visits and workflow", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    TextButton(onClick = { refresh() }, enabled = !loading) { Text("Refresh") }
                }
            }
            item(key = "overview") {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Overview", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            val metrics = listOf(
                Triple("Paid", summary?.totalPaid, statusTint("paid")),
                Triple("Pending", summary?.pending, statusTint("pending")),
                Triple("Assigned", summary?.assigned, statusTint("assigned")),
                Triple("Scheduled", summary?.scheduled, statusTint("scheduled")),
                Triple("In Progress", summary?.inProgress, statusTint("in_progress")),
                Triple("Completed", summary?.completed, statusTint("completed")),
                Triple("Cancelled", summary?.cancelled, statusTint("cancelled"))
            )
            BoxWithConstraints(Modifier.fillMaxWidth()) {
                val columns = 2
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    metrics.chunked(columns).forEach { rowMetrics ->
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            rowMetrics.forEach { (label, count, tint) ->
                                Card(
                                    Modifier.weight(1f).height(124.dp),
                                    colors = CardDefaults.cardColors(containerColor = tint.copy(alpha = 0.10f)),
                                    border = BorderStroke(1.dp, tint.copy(alpha = 0.22f)),
                                    shape = androidx.compose.foundation.shape.RoundedCornerShape(16.dp)
                                ) {
                                    Column(
                                        Modifier.fillMaxSize().padding(horizontal = 12.dp, vertical = 12.dp),
                                        verticalArrangement = Arrangement.spacedBy(8.dp)
                                    ) {
                                        Text(count?.toString() ?: "—", style = MaterialTheme.typography.titleLarge, color = tint, fontWeight = FontWeight.Bold, maxLines = 1)
                                        Text(label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 2)
                                    }
                                }
                            }
                            if (rowMetrics.size < columns) Spacer(Modifier.weight(1f))
                        }
                    }
                }
            }
                }
            }
            item(key = "booking_filters") {
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text("Filter bookings", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                filters.forEach { (key, label) ->
                    val count = summaryCounts[key]
                    FilterChip(
                        selected = filter == key,
                        onClick = {
                            filter = key
                            refresh(key.takeUnless { it == "all" })
                        },
                        label = { Text(if (count == null) label else "$label  $count", maxLines = 1) }
                    )
                }
            }
                }
            }
            if (error != null) {
                item(key = "load_error") {
                    Text(error!!, color = MaterialTheme.colorScheme.error)
                }
            }
            if (loading && rows.isEmpty()) {
                item(key = "initial_loading") {
                    Column(Modifier.fillMaxWidth().padding(32.dp), horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally) {
                        CircularProgressIndicator()
                    }
                }
            }
            if (loading && rows.isNotEmpty()) {
                item(key = "refreshing") {
                    Text("Refreshing bookings…", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
            if (!loading && error == null && rows.isEmpty()) {
                item(key = "empty_bookings") {
                    Text("No Site Visits match this filter.", color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(18.dp))
                }
            }
            items(rows, key = { it.id }) { row ->
                SiteVisitBookingCard(row, onClick = { onOpenBooking(row.id) })
            }
        }
    }
}

@Composable
private fun SiteVisitBookingCard(row: SiteVisitListItemDto, onClick: () -> Unit) {
    val tint = statusTint(row.status)
    Card(
        Modifier.fillMaxWidth().clickable(onClick = onClick),
        shape = androidx.compose.foundation.shape.RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Column(Modifier.weight(1f).padding(end = 10.dp)) {
                    Text("Site Visit Booking #${row.id}", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(row.propertyName, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold, maxLines = 2)
                }
                StatusBadge(row.status, tint)
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                VisitDateTimePill(formatSiteVisitDateTime(row.visitDate, row.visitTime))
                InfoPill("Payment ${row.paymentStatus.replace('_', ' ')}", statusTint("payment_${row.paymentStatus}"))
            }
            Text("Buyer  ${row.buyerName}  ·  ${row.buyerMobile}", style = MaterialTheme.typography.bodyMedium, maxLines = 2)
            Text("Field Officer  ${row.officer?.fullname ?: "Unassigned"}", style = MaterialTheme.typography.bodyMedium, maxLines = 1)
            Text("Listing #${row.listingId}", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun StatusBadge(label: String, tint: Color) {
    androidx.compose.material3.Surface(color = tint.copy(alpha = 0.12f), shape = androidx.compose.foundation.shape.RoundedCornerShape(50)) {
        Text(label.replace('_', ' ').replaceFirstChar { it.uppercase() }, color = tint, style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.SemiBold, maxLines = 1, modifier = Modifier.padding(horizontal = 11.dp, vertical = 6.dp))
    }
}

@Composable
private fun InfoPill(label: String, tint: Color = MaterialTheme.colorScheme.onSurfaceVariant) {
    androidx.compose.material3.Surface(color = tint.copy(alpha = 0.09f), shape = androidx.compose.foundation.shape.RoundedCornerShape(50)) {
        Text(label, color = tint, style = MaterialTheme.typography.labelMedium, maxLines = 1,
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp))
    }
}

@Composable
private fun VisitDateTimePill(label: String) {
    androidx.compose.material3.Surface(
        color = Color(0xFFEAF2FF),
        shape = androidx.compose.foundation.shape.RoundedCornerShape(12.dp)
    ) {
        Text(
            label,
            color = Color(0xFF1D4ED8),
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.Bold,
            maxLines = 1,
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp)
        )
    }
}

private fun statusTint(status: String): Color = when (status.lowercase()) {
    "pending" -> Color(0xFFB45309)
    "correction_required" -> Color(0xFF7E22CE)
    "assigned" -> Color(0xFF2563EB)
    "scheduled" -> Color(0xFF0891B2)
    "in_progress" -> Color(0xFF15803D)
    "completed" -> Color(0xFF166534)
    "cancelled" -> Color(0xFFB91C1C)
    "paid" -> Color(0xFF0F766E)
    else -> Color(0xFF475569)
}

private fun assignmentActionError(error: Throwable, fallback: String): String {
    val httpError = error as? HttpException
    val detail = httpError?.response()?.errorBody()?.let { body ->
        runCatching { safeSiteVisitErrorDetail(body.string()) }.getOrNull()
    }
    if (detail != null) return when (detail) {
        "Site Visit request cannot be unassigned in its current state" ->
            detail
        "Site Visit request cannot be assigned in its current state" ->
            "This booking is no longer eligible for assignment in its current state. Refresh the booking."
        "Field Officer is not eligible for assignment" ->
            "That Field Officer is no longer active or eligible. Refresh the officer list and choose another."
        "Not authorized" -> "Your Admin account is not authorized to change this assignment."
        else -> detail
    }
    if (httpError != null) return when (httpError.code()) {
        401 -> "Your session is no longer authorized. Sign in again and retry."
        403 -> "Your Admin account is not authorized to change this assignment."
        409 -> "The booking state changed before the request completed. Refresh booking details and retry if it remains eligible."
        422 -> "The backend rejected the assignment request. Refresh the booking and try again."
        else -> "The backend rejected the request (HTTP ${httpError.code()})."
    }
    if (error is IOException) return "Could not reach the backend. Check the connection and retry."
    return fallback
}

private fun fieldOfficerActionError(error: Throwable, fallback: String): String {
    val httpError = error as? HttpException
    val responseBody = httpError?.response()?.errorBody()?.let { body ->
        runCatching { body.string() }.getOrNull()
    }
    val rawDetail = responseBody?.let { body ->
        runCatching { JSONObject(body).opt("detail") as? String }.getOrNull()
    }
    val detail = when (rawDetail) {
        "Only the assigned active Field Officer can perform this action" ->
            "This booking is no longer assigned to your active account. Refresh your visits."
        "Site Visit payment must be successful before completion can be initiated" ->
            "Payment must be successful before completion can be initiated. Refresh the booking and retry if eligible."
        "Site Visit must be In Progress before completion can be initiated" ->
            "Start the visit before initiating completion. Refresh the booking and retry if eligible."
        "Site Visit request cannot initiate completion before it has started" ->
            "Start the visit before initiating completion. Refresh the booking and retry."
        "Site Visit payment must be successful before completion can be verified" ->
            "Payment must be successful before completion can be verified. Refresh the booking."
        "Site Visit must be In Progress before completion can be verified",
        "Site Visit request cannot be completed before it has started" ->
            "This visit is no longer eligible for completion. Refresh the booking and check its current status."
        "No active Site Visit completion code" ->
            "No active buyer code is available. Ask the buyer to refresh My Site Visits after you initiate completion."
        "Site Visit completion code has expired; Field Officer may initiate a new code" ->
            "The buyer's code expired. Initiate a new code and ask the buyer to refresh My Site Visits."
        "Site Visit completion code is invalid" ->
            "That code is incorrect. Confirm the current code with the buyer and retry."
        "Site Visit completion code has already been used" ->
            "This code has already been used. Refresh the booking to see its latest status."
        "Site Visit completion code attempts are locked" ->
            "Completion attempts are locked. Contact support before retrying."
        "Completion service is temporarily unavailable. Please try again later." ->
            "Completion service is temporarily unavailable. Check your connection and retry shortly."
        "Completion could not be processed. Please retry shortly." ->
            "Completion could not be processed. Refresh the booking and retry shortly."
        else -> responseBody?.let(::safeSiteVisitErrorDetail)
    }
    if (detail != null) return detail
    if (httpError != null) return when (httpError.code()) {
        401 -> "Your session expired. Sign in again and retry."
        403 -> "Only the currently assigned active Field Officer can perform this action."
        404 -> "This booking was not found in your assigned visits. Refresh the list."
        503 -> "Completion service is temporarily unavailable. Check your connection and retry shortly."
        409 -> "The booking state changed or the code is no longer valid. Refresh the booking and retry if eligible."
        429 -> "Too many completion attempts. Contact support before retrying."
        else -> "$fallback (HTTP ${httpError.code()})."
    }
    if (error is IOException) return "Could not reach the backend. Check the connection and retry."
    return fallback
}

private fun safeSiteVisitErrorDetail(responseBody: String): String? {
    val detail = runCatching { JSONObject(responseBody).opt("detail") }.getOrNull()
    val text = when (detail) {
        is String -> detail
        is org.json.JSONArray -> (0 until detail.length()).mapNotNull { index ->
            val item = detail.optJSONObject(index) ?: return@mapNotNull null
            item.optString("msg").takeIf { it.isNotBlank() }
        }.joinToString("; ")
        is JSONObject -> detail.optString("message").takeIf { it.isNotBlank() }
        else -> null
    }?.trim()?.takeIf { it.isNotEmpty() }
    if (text == null) return null
    return if (Regex("(?i)(upi|completion.?code|password|authorization|signature|token|credential)").containsMatchIn(text)) {
        "The backend returned a sensitive error detail. Review server logs securely."
    } else {
        text.take(400)
    }
}

private fun logUnassignmentOutcome(bookingId: Int, httpStatus: Int?, outcome: String, detail: String? = null) {
    if (!BuildConfig.DEBUG) return
    val safeDetail = detail?.replace(Regex("[\\r\\n]+"), " ")?.take(240) ?: "none"
    Log.i(
        "AdminSiteVisit",
        "unassign booking_id=$bookingId http_status=${httpStatus ?: "unavailable"} outcome=$outcome detail=$safeDetail"
    )
}

private fun unassignmentHttpError(status: Int): String = when (status) {
    401 -> "Your session is no longer authorized. Sign in again and retry."
    403 -> "Your Admin account is not authorized to change this assignment."
    409 -> "The booking state changed before the request completed. Refresh booking details and retry if it remains eligible."
    422 -> "The backend rejected the unassignment request. Refresh the booking and try again."
    else -> "The backend rejected the unassignment request (HTTP $status)."
}

@Composable
fun AdminSiteVisitBookingDetailScreen(bookingId: Int, onBack: () -> Unit, onBookingUpdated: () -> Unit = {}) {
    val api = ApiClient.siteVisitApi
    val scope = rememberCoroutineScope()
    var item by remember(bookingId) { mutableStateOf<SiteVisitDetailDto?>(null) }
    var officers by remember(bookingId) { mutableStateOf<List<com.example.mybroker_admin.data.remote.dto.AdminFieldOfficerOptionDto>>(emptyList()) }
    var selectedOfficer by remember(bookingId) { mutableStateOf<com.example.mybroker_admin.data.remote.dto.AdminFieldOfficerOptionDto?>(null) }
    var showOfficerPicker by remember(bookingId) { mutableStateOf(false) }
    var confirmUnassign by remember(bookingId) { mutableStateOf(false) }
    var actionKind by remember(bookingId) { mutableStateOf<String?>(null) }
    var actionReason by remember(bookingId) { mutableStateOf("") }
    var actionLoading by remember(bookingId) { mutableStateOf(false) }
    var loading by remember(bookingId) { mutableStateOf(true) }
    var error by remember(bookingId) { mutableStateOf<String?>(null) }
    var message by remember(bookingId) { mutableStateOf<String?>(null) }
    BackHandler(enabled = actionKind == null, onBack = onBack)

    suspend fun reloadBooking() {
        loading = true
        error = null
        try {
            val details = api.detail(bookingId)
            item = details
            val officerResult = runCatching { ApiClient.adminListingApi.getFieldOfficers() }
            officers = officerResult.getOrElse {
                emptyList()
            }
            if (officerResult.isFailure && details.status in setOf("pending", "assigned", "in_progress")) {
                error = "Could not load active eligible Field Officers. Refresh before assigning or reassigning."
            }
        } catch (e: Exception) {
            error = "Could not load Site Visit booking #$bookingId. Check access or connection."
        } finally {
            loading = false
        }
    }
    fun refresh() = scope.launch { reloadBooking() }
    LaunchedEffect(bookingId) { refresh() }

    Scaffold { inset ->
        Column(Modifier.fillMaxSize().padding(inset).padding(horizontal = 18.dp, vertical = 12.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                TextButton(onClick = onBack) { Text("← Back to bookings") }
                TextButton(onClick = { refresh() }, enabled = !loading && !actionLoading) { Text("Refresh") }
            }
            error?.let { Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(12.dp)) }
            message?.let { Text(it, color = Color(0xFF15803D), modifier = Modifier.padding(horizontal = 12.dp)) }
            if (loading && item == null) {
                Column(Modifier.weight(1f).fillMaxWidth(), horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                    CircularProgressIndicator()
                }
            }
            item?.let { booking ->
                val hasProgress = booking.scheduledAt != null || booking.startedAt != null ||
                    booking.completedAt != null || booking.cancelledAt != null
                val activeVisit = booking.status == "in_progress"
                val canMutateAssignment = !hasProgress && (
                    (booking.status == "pending" && booking.officer == null) ||
                        (booking.status == "assigned" && booking.officer != null)
                    )
                val canOverrideAssignment = activeVisit
                Column(
                    Modifier.weight(1f).fillMaxWidth().verticalScroll(rememberScrollState()).padding(bottom = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Column(Modifier.weight(1f).padding(end = 10.dp)) {
                            Text("Site Visit Booking #${booking.id}", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text(booking.propertyName, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                        }
                        StatusBadge(booking.status, statusTint(booking.status))
                    }
                    DetailSection("Booking Information") {
                        DetailLine("Booking ID", booking.id.toString())
                        DetailLine("Listing ID", booking.listingId.toString())
                        DetailLine("Listing code", booking.listingCode ?: "—")
                        DetailLine("Property", booking.propertyName)
                        DetailLine("Preferred visit", "${formatSiteVisitDate(booking.visitDate)} · ${formatSiteVisitTime(booking.visitTime)}")
                        DetailLine("Visitors", booking.visitorCount.toString())
                        DetailLine("Pickup address", booking.pickupAddress)
                        DetailLine("Additional message", booking.message ?: "—")
                        DetailLine("Site Visit fee", "₹${booking.fee}")
                    }
                    DetailSection("Buyer Information") {
                        DetailLine("Buyer", booking.buyerName)
                        DetailLine("Mobile", booking.buyerMobile)
                    }
                    DetailSection("Payment Information") {
                        DetailLine("Payment status", booking.paymentStatus.replace('_', ' ').replaceFirstChar { it.uppercase() })
                    }
                    Text("Assignment", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    if (booking.officer == null) {
                        Card(
                            Modifier.fillMaxWidth(),
                            shape = androidx.compose.foundation.shape.RoundedCornerShape(16.dp),
                            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f))
                        ) {
                            Column(Modifier.fillMaxWidth().padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                Text("No Field Officer Assigned", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                                if (canMutateAssignment || canOverrideAssignment) {
                                    Button(enabled = !actionLoading, onClick = {
                                        showOfficerPicker = true
                                    }) { Text("Assign Field Officer") }
                                } else {
                                    Text("Assignment is unavailable for this booking status.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                            }
                        }
                    } else {
                        val assigned = booking.officer!!
                        val assignedProfile = officers.firstOrNull { it.id == assigned.id }
                        Card(
                            Modifier.fillMaxWidth(),
                            shape = androidx.compose.foundation.shape.RoundedCornerShape(18.dp),
                            border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.32f)),
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.35f))
                        ) {
                            Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                                Text(assignedProfile?.fullname ?: assigned.fullname ?: "Field Officer #${assigned.id}", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                                Text("Officer ID  #${assigned.id}", color = MaterialTheme.colorScheme.onSurfaceVariant)
                                Text("Mobile  ${assignedProfile?.mobile?.takeIf { it.isNotBlank() } ?: "Unavailable"}")
                                Text("State and district  Unavailable")
                                    Text("Status  ${if (assignedProfile == null) "Unavailable" else if (assignedProfile.is_active) "Active" else "Inactive"}", color = MaterialTheme.colorScheme.onSurfaceVariant)
                                androidx.compose.material3.Divider()
                                Text("FIELD OFFICER", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
                                Text((assignedProfile?.fullname ?: assigned.fullname ?: "Field Officer #${assigned.id}").uppercase(), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.ExtraBold)
                                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    Button(
                                        modifier = Modifier.weight(1f),
                                        enabled = !actionLoading && (booking.status == "assigned" && !hasProgress || activeVisit),
                                        onClick = { showOfficerPicker = true }
                                    ) { Text("Change Field Officer") }
                                    TextButton(
                                        modifier = Modifier.weight(1f),
                                        enabled = !actionLoading && (booking.status == "assigned" && !hasProgress || activeVisit),
                                        onClick = {
                                            if (activeVisit) {
                                                actionKind = "active_unassignment"
                                                actionReason = ""
                                            } else confirmUnassign = true
                                        }
                                    ) { Text("Unassign Field Officer") }
                                }
                                if (!canMutateAssignment && !activeVisit) {
                                    Text("Assignment changes are unavailable for this booking status.", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                                }
                            }
                        }
                        selectedOfficer?.takeIf { it.id != assigned.id }?.let { chosen ->
                            OfficerProfileCard(
                                heading = "SELECTED OFFICER PREVIEW",
                                officerId = chosen.id,
                                name = chosen.fullname,
                                mobile = chosen.mobile,
                                active = chosen.is_active
                            )
                            Button(
                                enabled = !actionLoading && (booking.status == "assigned" && !hasProgress || activeVisit),
                                onClick = {
                                    if (activeVisit) {
                                        actionKind = "active_assignment"
                                        actionReason = ""
                                    } else {
                                    scope.launch {
                                        actionLoading = true
                                        error = null
                                        message = null
                                        try {
                                            api.assign(booking.id, SiteVisitAssignmentRequestDto(chosen.id))
                                            selectedOfficer = null
                                            message = "Field Officer reassigned for booking #${booking.id}."
                                            onBookingUpdated()
                                            reloadBooking()
                                        } catch (e: Exception) {
                                            error = assignmentActionError(e, "Reassignment failed. Refresh and review booking status and officer eligibility.")
                                        } finally {
                                            actionLoading = false
                                        }
                                    }
                                    }
                                }
                            ) { Text(if (actionLoading) "Reassigning…" else "Confirm Reassignment") }
                        }
                    }
                    if (booking.officer == null && selectedOfficer != null) {
                        OfficerProfileCard(
                            heading = "SELECTED OFFICER PREVIEW",
                            officerId = selectedOfficer!!.id,
                            name = selectedOfficer!!.fullname,
                            mobile = selectedOfficer!!.mobile,
                            active = selectedOfficer!!.is_active
                        )
                        Button(
                            enabled = !actionLoading,
                            onClick = {
                                val chosen = selectedOfficer ?: return@Button
                                if (activeVisit) {
                                    actionKind = "active_assignment"
                                    actionReason = ""
                                    return@Button
                                }
                                scope.launch {
                                    actionLoading = true
                                    error = null
                                    message = null
                                    try {
                                        api.assign(booking.id, SiteVisitAssignmentRequestDto(chosen.id))
                                        selectedOfficer = null
                                        message = "Field Officer assigned to booking #${booking.id}."
                                        onBookingUpdated()
                                        reloadBooking()
                                    } catch (e: Exception) {
                                        error = assignmentActionError(e, "Assignment failed. Refresh and review booking status and officer eligibility.")
                                    } finally {
                                        actionLoading = false
                                    }
                                }
                            }
                        ) { Text(if (actionLoading) "Assigning…" else "Confirm Assignment") }
                    }
                    DetailSection("Assignment History") {
                        if (booking.history.isEmpty()) Text("No assignment history.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                        booking.history.forEach { history ->
                            Column(verticalArrangement = Arrangement.spacedBy(3.dp), modifier = Modifier.padding(vertical = 5.dp)) {
                                Text("${history.action.replace('_', ' ')} · ${history.createdAt}", fontWeight = FontWeight.SemiBold)
                                history.actor?.let { Text("By ${it.fullname ?: "User #${it.id}"}") }
                                history.previousOfficer?.let { Text("Previous officer: ${it.fullname ?: "Officer #${it.id}"}") }
                                history.fieldOfficer?.let { Text("Field Officer: ${it.fullname ?: "Officer #${it.id}"}") }
                                history.note?.let { Text("Note: $it") }
                            }
                        }
                    }
                    DetailSection("Workflow Information") {
                        DetailLine("Current status", booking.status.replace('_', ' ').replaceFirstChar { it.uppercase() })
                        DetailLine("Started", booking.startedAt ?: "—")
                        DetailLine("Completed", booking.completedAt ?: "—")
                        DetailLine("Correction reason", booking.correctionReason ?: "—")
                        DetailLine("Cancellation reason", booking.cancellationReason ?: "—")
                        booking.cancellationActorRole?.let { DetailLine("Cancelled by role", it) }
                        booking.cancelledById?.let { DetailLine("Cancelled by user", "#$it") }
                        if (booking.workflowHistory.isEmpty()) Text("No workflow history.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                        booking.workflowHistory.forEach { event ->
                            Column(verticalArrangement = Arrangement.spacedBy(3.dp), modifier = Modifier.padding(vertical = 5.dp)) {
                                Text("${event.eventType.replace('_', ' ')} · ${event.actorRole} #${event.actorId}", fontWeight = FontWeight.SemiBold)
                                Text(event.createdAt)
                                event.reason?.let { Text("Reason: $it") }
                                event.previousValues?.let { Text("Before: ${it.entries.joinToString { entry -> "${entry.key}: ${entry.value}" }}") }
                                event.updatedValues?.let { Text("After: ${it.entries.joinToString { entry -> "${entry.key}: ${entry.value}" }}") }
                            }
                        }
                    }
                    if (booking.status == "pending") {
                        Button(enabled = !actionLoading, onClick = { actionKind = "correction"; actionReason = "" }) { Text("Request Correction") }
                    }
                    DetailSection("Booking Actions") {
                        Button(
                            enabled = !actionLoading && booking.status in setOf("pending", "correction_required", "assigned", "scheduled", "in_progress"),
                            onClick = { actionKind = "cancel"; actionReason = "" }
                        ) { Text("Cancel Booking") }
                        if (!activeVisit && booking.status !in setOf("pending", "correction_required", "assigned", "scheduled")) {
                            Text("Cancellation is unavailable for this booking status.", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
            item?.let { actionBooking -> actionKind?.let { kind ->
                AlertDialog(
                    onDismissRequest = { if (!actionLoading) actionKind = null },
                    title = {
                        Text(when (kind) {
                            "correction" -> "Request buyer correction"
                            "active_assignment" -> "Confirm active visit reassignment"
                            "active_unassignment" -> "Confirm active visit unassignment"
                            else -> if (actionBooking.status == "in_progress") "Confirm active visit cancellation" else "Cancel Site Visit"
                        })
                    },
                    text = {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            if (kind != "correction") {
                                Text(when (kind) {
                                    "active_assignment" -> "This override will be recorded with your account and reason. The visit remains In Progress."
                                    "active_unassignment" -> "The visit remains In Progress and the current officer will lose access to this booking."
                                    else -> "This permanently cancels the active visit. A refund case may be opened for Accounting; no payment is issued automatically."
                                })
                            }
                            OutlinedTextField(actionReason, { actionReason = it }, label = { Text("Mandatory reason") }, modifier = Modifier.fillMaxWidth())
                        }
                    },
                    confirmButton = {
                        Button(enabled = actionReason.trim().length >= 3 && !actionLoading, onClick = {
                            val reason = actionReason.trim()
                            scope.launch {
                                actionLoading = true
                                error = null
                                message = null
                                try {
                                    val request = SiteVisitAdminActionRequestDto(reason)
                                    when (kind) {
                                        "correction" -> api.requestCorrection(actionBooking.id, request)
                                        "active_assignment" -> {
                                            val chosen = requireNotNull(selectedOfficer) { "Select an active Field Officer before confirming" }
                                            api.assign(actionBooking.id, SiteVisitAssignmentRequestDto(chosen.id, reason))
                                        }
                                        "active_unassignment" -> {
                                            val response = api.unassign(actionBooking.id, SiteVisitUnassignmentRequestDto(reason))
                                            if (!response.isSuccessful) throw HttpException(response)
                                        }
                                        else -> api.cancel(actionBooking.id, request)
                                    }
                                    message = if (kind == "correction") "Correction request recorded for booking #${actionBooking.id}."
                                    else when (kind) {
                                        "active_assignment" -> "Field Officer assignment updated for active booking #${actionBooking.id}."
                                        "active_unassignment" -> "Field Officer unassigned from active booking #${actionBooking.id}."
                                        else -> "Booking #${actionBooking.id} cancelled."
                                    }
                                    if (kind == "active_assignment") selectedOfficer = null
                                    actionKind = null
                                    actionReason = ""
                                    onBookingUpdated()
                                    reloadBooking()
                                } catch (e: Exception) {
                                    error = assignmentActionError(e, "The request was rejected. Refresh and review the current booking status.")
                                } finally {
                                    actionLoading = false
                                }
                            }
                        }) { Text(if (actionLoading) "Submitting…" else if (kind.startsWith("active_")) "Confirm Override" else "Submit") }
                    },
                    dismissButton = { TextButton(enabled = !actionLoading, onClick = { actionKind = null }) { Text("Keep booking") } }
                )
            } }
            item?.let { booking ->
                if (showOfficerPicker) {
                    AlertDialog(
                        onDismissRequest = { if (!actionLoading) showOfficerPicker = false },
                        title = { Text("Choose Field Officer") },
                        text = {
                            Column(modifier = Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                if (officers.isEmpty()) {
                                    Text("No active eligible Field Officers are available.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                                } else {
                                    LazyColumn(
                                        modifier = Modifier.fillMaxWidth().heightIn(max = 480.dp),
                                        verticalArrangement = Arrangement.spacedBy(8.dp)
                                    ) {
                                        items(officers, key = { it.id }) { officer ->
                                            val isSelected = selectedOfficer?.id == officer.id
                                            val isCurrent = booking.officer?.id == officer.id
                                            Card(
                                                Modifier.fillMaxWidth().clickable(enabled = !actionLoading && !isCurrent) {
                                                    selectedOfficer = officer
                                                    showOfficerPicker = false
                                                },
                                                shape = androidx.compose.foundation.shape.RoundedCornerShape(12.dp),
                                                border = BorderStroke(
                                                    if (isSelected || isCurrent) 2.dp else 1.dp,
                                                    if (isSelected || isCurrent) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant
                                                ),
                                                colors = CardDefaults.cardColors(
                                                    containerColor = if (isSelected || isCurrent) MaterialTheme.colorScheme.primaryContainer
                                                    else MaterialTheme.colorScheme.surface
                                                )
                                            ) {
                                                Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                                    Text(officer.fullname, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                                                    Text("Officer ID #${officer.id} · ${officer.mobile?.takeIf { it.isNotBlank() } ?: "Mobile unavailable"}")
                                                    Text("${if (officer.is_active) "Active" else "Inactive"} · State and district unavailable", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                                    when {
                                                        isSelected -> Text("Selected", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
                                                        isCurrent -> Text("Currently assigned", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        confirmButton = { TextButton(onClick = { showOfficerPicker = false }) { Text("Close") } }
                    )
                }
                if (confirmUnassign && booking.officer != null) {
                    AlertDialog(
                        onDismissRequest = { if (!actionLoading) confirmUnassign = false },
                        title = { Text("Unassign Field Officer?") },
                        text = { Text("Remove ${booking.officer.fullname ?: "Field Officer #${booking.officer.id}"} from Site Visit booking #${booking.id}?") },
                        confirmButton = {
                            Button(enabled = !actionLoading, onClick = {
                                scope.launch {
                                    actionLoading = true
                                    error = null
                                    message = null
                                    try {
                                        val response = api.unassign(booking.id, SiteVisitUnassignmentRequestDto())
                                        val responseBody = withContext(Dispatchers.IO) {
                                            if (response.isSuccessful) response.body()?.string()
                                            else response.errorBody()?.string()
                                        }
                                        val detail = responseBody?.let(::safeSiteVisitErrorDetail)
                                        if (!response.isSuccessful) {
                                            logUnassignmentOutcome(booking.id, response.code(), "rejected", detail)
                                            error = detail ?: unassignmentHttpError(response.code())
                                        } else {
                                            val result = runCatching { JSONObject(responseBody.orEmpty()) }.getOrNull()
                                            val resultStatus = result?.optString("status")
                                            val resultAction = result?.optString("action")
                                            if (resultStatus != "pending" || resultAction != "unassigned") {
                                                logUnassignmentOutcome(booking.id, response.code(), "invalid_success_response", detail)
                                                error = "The backend returned success without confirming the unassignment. Refresh booking details before retrying."
                                            } else {
                                                logUnassignmentOutcome(booking.id, response.code(), "success")
                                                // Change local assignment state only after the backend confirms it.
                                                item = booking.copy(status = "pending", officer = null)
                                                confirmUnassign = false
                                                selectedOfficer = null
                                                message = "Field Officer unassigned from booking #${booking.id}."
                                                onBookingUpdated()
                                                reloadBooking()
                                            }
                                        }
                                    } catch (e: Exception) {
                                        val httpError = e as? HttpException
                                        val detail = httpError?.response()?.errorBody()?.let { body ->
                                            runCatching { safeSiteVisitErrorDetail(body.string()) }.getOrNull()
                                        }
                                        logUnassignmentOutcome(
                                            booking.id,
                                            httpError?.code(),
                                            if (e is IOException) "transport_error" else "client_error",
                                            detail ?: e::class.java.simpleName
                                        )
                                        error = assignmentActionError(e, "Unassignment failed. Refresh and review the booking status.")
                                    } finally {
                                        actionLoading = false
                                    }
                                }
                            }) { Text(if (actionLoading) "Unassigning…" else "Confirm Unassign") }
                        },
                        dismissButton = { TextButton(enabled = !actionLoading, onClick = { confirmUnassign = false }) { Text("Keep Officer") } }
                    )
                }
            }
        }
    }
}

@Composable
private fun OfficerProfileCard(
    heading: String,
    officerId: Int,
    name: String,
    mobile: String?,
    active: Boolean?
) {
    Card(
        Modifier.fillMaxWidth(),
        shape = androidx.compose.foundation.shape.RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.28f))
    ) {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
            Text(heading, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
            Text(name, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text("Officer ID  #$officerId", color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text("Mobile  ${mobile?.takeIf { it.isNotBlank() } ?: "Unavailable"}")
            Text("State and district  Unavailable", color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text("Status  ${when (active) { true -> "Active"; false -> "Inactive"; null -> "Unavailable" }}", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun DetailSection(title: String, content: @Composable () -> Unit) {
    Card(Modifier.fillMaxWidth(), shape = androidx.compose.foundation.shape.RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            content()
        }
    }
}

@Composable
private fun DetailLine(label: String, value: String) {
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, style = MaterialTheme.typography.bodyLarge)
    }
}

@Composable
fun FieldOfficerSiteVisitsScreen(
    onOpenBooking: (Int) -> Unit = {},
    refreshKey: Long = 0L
) {
    val api = ApiClient.siteVisitApi
    val scope = rememberCoroutineScope()
    var visits by remember { mutableStateOf<List<FieldOfficerVisitDto>>(emptyList()) }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var filter by remember { mutableStateOf("all") }
    fun refresh() = scope.launch {
        loading = true
        error = null
        try {
            visits = sortFieldOfficerSiteVisits(api.myVisits())
        } catch (e: Exception) {
            error = "Could not load assigned visits."
        } finally { loading = false }
    }
    LaunchedEffect(refreshKey) { refresh() }
    val filters = listOf(
        "all" to "All", "assigned" to "Assigned", "scheduled" to "Scheduled",
        "in_progress" to "In Progress", "completed" to "Completed", "cancelled" to "Cancelled"
    )
    val visibleVisits = filterFieldOfficerSiteVisits(visits, filter)
    Scaffold { inset ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(inset),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 16.dp, vertical = 14.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            item(key = "field_visits_header") {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Column(Modifier.weight(1f).padding(end = 8.dp)) {
                        Text("My Assigned Site Visits", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                        Text("Visits currently assigned to your account", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    TextButton(onClick = { refresh() }, enabled = !loading) { Text("Refresh") }
                }
            }
            item(key = "field_visit_filters") {
                Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    filters.forEach { (key, label) ->
                        FilterChip(selected = filter == key, onClick = { filter = key }, label = { Text(label, maxLines = 1) })
                    }
                }
            }
            if (loading && visits.isEmpty()) {
                item(key = "field_visits_loading") {
                    androidx.compose.foundation.layout.Box(Modifier.fillMaxWidth().padding(28.dp), contentAlignment = androidx.compose.ui.Alignment.Center) {
                        CircularProgressIndicator()
                    }
                }
            }
            if (loading && visits.isNotEmpty()) item(key = "field_visits_refreshing") {
                Text("Refreshing assigned visits…", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            error?.let { currentError ->
                item(key = "field_visits_error") { Text(currentError, color = MaterialTheme.colorScheme.error) }
            }
            if (!loading && error == null && visibleVisits.isEmpty()) {
                item(key = "field_visits_empty") {
                    Text(
                        if (filter == "all") "No Site Visits are assigned to you yet." else "No ${filter.replace('_', ' ')} visits.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(18.dp)
                    )
                }
            }
            items(visibleVisits, key = { it.id }) { visit ->
                FieldOfficerVisitCard(visit) { onOpenBooking(visit.id) }
            }
        }
    }
}

@Composable
private fun FieldOfficerVisitCard(visit: FieldOfficerVisitDto, onClick: () -> Unit) {
    val tint = statusTint(visit.status)
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        shape = androidx.compose.foundation.shape.RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Column(Modifier.weight(1f).padding(end = 8.dp)) {
                    Text("Site Visit Booking #${visit.id}", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(visit.propertyName, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold, maxLines = 2)
                }
                StatusBadge(visit.status, tint)
            }
            Text(
                "Listing #${visit.listingId}  ·  ${visit.listingCode ?: "Code unavailable"}",
                style = MaterialTheme.typography.bodyMedium,
                maxLines = 1,
                overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis
            )
            VisitDateTimePill(formatSiteVisitDateTime(visit.visitDate, visit.visitTime))
            Row(Modifier.fillMaxWidth(), verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                Text("${visit.visitorCount} visitor(s)", modifier = Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
                Text(
                    "Payment ${visit.paymentStatus.replace('_', ' ')}",
                    style = MaterialTheme.typography.labelMedium,
                    color = statusTint("payment_${visit.paymentStatus}"),
                    maxLines = 1,
                    overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis
                )
            }
            Text("Tap to view booking details  ›", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
        }
    }
}

@Composable
fun FieldOfficerSiteVisitDetailScreen(
    bookingId: Int,
    onBack: () -> Unit,
    onBookingUpdated: () -> Unit = {}
) {
    val api = ApiClient.siteVisitApi
    val scope = rememberCoroutineScope()
    var visit by remember(bookingId) { mutableStateOf<FieldOfficerVisitDto?>(null) }
    var bookingAuthorized by remember(bookingId) { mutableStateOf(false) }
    var code by remember(bookingId) { mutableStateOf("") }
    var loading by remember { mutableStateOf(false) }
    var actionLoading by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf<String?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    fun refresh(actionError: String? = null) = scope.launch {
        loading = true
        bookingAuthorized = false
        error = null
        var refreshed = false
        try {
            visit = api.myVisits().firstOrNull { it.id == bookingId }
            bookingAuthorized = visit != null
            refreshed = true
            if (visit == null) error = "Booking #$bookingId is no longer assigned to your account."
        } catch (e: Exception) {
            error = actionError?.let { "$it Booking status could not be refreshed; tap Refresh to retry." }
                ?: "Could not load this assigned visit. Tap Refresh to retry."
        } finally {
            loading = false
            if (actionError != null && refreshed) error = actionError
        }
    }
    fun afterActionSuccess(successMessage: String, updatedStatus: String? = null) {
        updatedStatus?.let { status -> visit = visit?.copy(status = status) }
        message = successMessage
        onBookingUpdated()
        refresh()
    }
    LaunchedEffect(bookingId) { refresh() }
    val currentVisit = visit
    LaunchedEffect(bookingId, currentVisit?.status) {
        if (siteVisitMapVisible(currentVisit?.status)) {
            while (true) {
                delay(30_000L)
                try {
                    val latest = api.myVisits().firstOrNull { it.id == bookingId }
                    visit = latest
                    bookingAuthorized = latest != null
                    if (latest == null) error = "Booking #$bookingId is no longer assigned to your account."
                } catch (_: Exception) {
                    bookingAuthorized = false
                    error = "Could not confirm this booking is still assigned. Refresh to retry."
                }
            }
        }
    }
    Scaffold { inset ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(inset),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 18.dp, vertical = 14.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item(key = "field_visit_detail_header") {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Column(Modifier.weight(1f).padding(end = 8.dp)) {
                        Text("Assigned Site Visit", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                        Text("Booking #$bookingId", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    TextButton(onClick = onBack) { Text("Back") }
                }
                TextButton(onClick = { refresh() }, enabled = !loading) { Text("Refresh booking") }
            }
            if (loading && currentVisit == null) item(key = "field_visit_detail_loading") {
                androidx.compose.foundation.layout.Box(Modifier.fillMaxWidth().padding(28.dp), contentAlignment = androidx.compose.ui.Alignment.Center) {
                    CircularProgressIndicator()
                }
            }
            error?.let { currentError -> item(key = "field_visit_detail_error") { Text(currentError, color = MaterialTheme.colorScheme.error) } }
            message?.let { currentMessage -> item(key = "field_visit_detail_message") { Text(currentMessage, color = MaterialTheme.colorScheme.primary) } }
            if (actionLoading) item(key = "field_visit_action_loading") {
                LinearProgressIndicator(Modifier.fillMaxWidth())
            }
            currentVisit?.let { selected ->
                item(key = "field_visit_booking_info") {
                    DetailSection("Booking and listing") {
                        Text(selected.propertyName, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                        DetailLine("Booking ID", "#${selected.id}")
                        DetailLine("Listing", "#${selected.listingId}  ·  ${selected.listingCode ?: "Code unavailable"}")
                        DetailLine("Fee", "₹${selected.fee}")
                        VisitDateTimePill(formatSiteVisitDateTime(selected.visitDate, selected.visitTime))
                        DetailLine("Visitors", selected.visitorCount.toString())
                        DetailLine("Payment", selected.paymentStatus.replace('_', ' '))
                    }
                }
                if (siteVisitMapVisible(selected.status)) {
                    item(key = "field_visit_live_map") {
                        FieldOfficerSiteVisitLiveMap(
                            status = selected.status,
                            bookingStillAssigned = bookingAuthorized,
                            boundaryPoints = selected.landBoundaryPoints
                        )
                    }
                }
                item(key = "field_visit_buyer_info") {
                    DetailSection("Buyer") {
                        DetailLine("Name", selected.buyerName)
                        DetailLine("Mobile", selected.buyerMobile)
                    }
                }
                item(key = "field_visit_visit_info") {
                    DetailSection("Visit details") {
                        DetailLine("Pickup address", selected.pickupAddress)
                        DetailLine("Additional message", selected.message?.takeIf { it.isNotBlank() } ?: "None")
                    }
                }
                item(key = "field_visit_assignment_info") {
                    DetailSection("Assignment and workflow") {
                        DetailLine("Assigned to", "Your account")
                        selected.assignedAt?.let { DetailLine("Assigned at", it.replace('T', ' ').take(16)) }
                        selected.assignmentNote?.takeIf { it.isNotBlank() }?.let { DetailLine("Admin assignment note", it) }
                        DetailLine("Current status", selected.status.replace('_', ' '))
                        selected.startedAt?.let { DetailLine("Started at", it.replace('T', ' ').take(16)) }
                        selected.completedAt?.let { DetailLine("Completed at", it.replace('T', ' ').take(16)) }
                    }
                }
                item(key = "field_visit_actions") {
                    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        if (selected.status == "assigned" || selected.status == "scheduled") {
                            Button(
                                modifier = Modifier.fillMaxWidth(),
                                enabled = !loading && !actionLoading,
                                onClick = { scope.launch {
                                    actionLoading = true
                                    runCatching { api.start(selected.id) }
                                        .onSuccess { result -> afterActionSuccess("Visit started.", result.status) }
                                        .onFailure { refresh(fieldOfficerActionError(it, "Start request was rejected.")) }
                                    actionLoading = false
                                } }
                            ) { Text(if (actionLoading) "Starting…" else "Start visit") }
                        }
                        if (selected.status == "in_progress") {
                            Button(
                                modifier = Modifier.fillMaxWidth(),
                                enabled = !loading && !actionLoading,
                                onClick = { scope.launch {
                                    actionLoading = true
                                    runCatching { api.initiateCompletion(selected.id) }
                                        .onSuccess { afterActionSuccess("Completion is ready. Ask the buyer to refresh My Site Visits and share the active code with you.") }
                                        .onFailure { refresh(fieldOfficerActionError(it, "Could not initiate completion.")) }
                                    actionLoading = false
                                } }
                            ) { Text(if (actionLoading) "Preparing completion…" else "Initiate completion") }
                            OutlinedTextField(
                                code,
                                { code = it.filter(Char::isDigit).take(6) },
                                label = { Text("Buyer completion code") },
                                modifier = Modifier.fillMaxWidth(),
                                enabled = !actionLoading
                            )
                            Button(
                                modifier = Modifier.fillMaxWidth(),
                                enabled = code.length == 6 && !actionLoading && !loading,
                                onClick = { scope.launch {
                                    actionLoading = true
                                    runCatching { api.verifyCompletion(selected.id, CompletionCodeRequestDto(code)) }
                                        .onSuccess { result -> code = ""; afterActionSuccess("Visit completed.", result.status) }
                                        .onFailure { refresh(fieldOfficerActionError(it, "Code verification failed.")) }
                                    actionLoading = false
                                } }
                            ) { Text(if (actionLoading) "Verifying…" else "Verify and complete") }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun AccountingSiteVisitRefundsScreen(
    initialBookingId: Int? = null,
    refreshKey: Int = 0,
    onBack: () -> Unit = {},
    onRefundClick: (Int) -> Unit = {}
) {
    val api = ApiClient.siteVisitApi
    val scope = rememberCoroutineScope()
    var summary by remember { mutableStateOf<SiteVisitAccountingSummaryDto?>(null) }
    var awaitingUpi by remember { mutableStateOf(0) }
    var items by remember { mutableStateOf<List<SiteVisitAccountingRefundDto>>(emptyList()) }
    var total by remember { mutableStateOf(0) }
    var skip by remember { mutableStateOf(0) }
    var filter by remember { mutableStateOf<String?>(null) }
    var search by remember(initialBookingId) { mutableStateOf(initialBookingId?.toString().orEmpty()) }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var message by remember { mutableStateOf<String?>(null) }
    fun refresh() = scope.launch {
        loading = true
        error = null
        try {
            summary = api.accountingSummary()
            awaitingUpi = api.accountingRefunds(skip = 0, limit = 1, status = "pending_details").total
            val page = api.accountingRefunds(skip = skip, limit = 25, status = filter, search = search.trim().ifBlank { null })
            items = page.items
            total = page.total
        } catch (e: Exception) {
            error = "Could not load Site Visit accounting data. Check your Accounting access or connection."
        } finally { loading = false }
    }
    LaunchedEffect(initialBookingId, refreshKey, skip, filter) { refresh() }
    val counts = summary
    Scaffold { inset ->
        Column(Modifier.fillMaxSize().padding(inset).padding(horizontal = 16.dp, vertical = 12.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Column(Modifier.weight(1f)) {
                    Text("Site Visit Refunds", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                    Text("Accounting overview and refund cases", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                TextButton(onClick = onBack) { Text("Back") }
            }
            TextButton(onClick = { refresh() }, enabled = !loading) { Text(if (loading) "Refreshing…" else "Refresh") }
            counts?.let { data ->
                val cards = listOf(
                    RefundSummaryCard("Total bookings", data.totalBookings, Color(0xFFEAF2FF), Color(0xFF1D4ED8)),
                    RefundSummaryCard("Paid bookings", data.paid, Color(0xFFE5F8F0), Color(0xFF047857)),
                    RefundSummaryCard("Pending payments", data.pendingPayments, Color(0xFFFFF4DB), Color(0xFFB45309)),
                    RefundSummaryCard("Refund cases", data.refundRequests, Color(0xFFF1EAFE), Color(0xFF6D28D9)),
                    RefundSummaryCard("Awaiting UPI", awaitingUpi, Color(0xFFFFF0E5), Color(0xFFC2410C)),
                    RefundSummaryCard("Pending refunds", data.refundPending, Color(0xFFE7F5FA), Color(0xFF0E7490)),
                    RefundSummaryCard("Refunded", data.refunded, Color(0xFFE9F7E9), Color(0xFF15803D)),
                    RefundSummaryCard("Failed refunds", data.refundFailed, Color(0xFFFFE9E9), Color(0xFFB91C1C))
                )
                BoxWithConstraints(Modifier.fillMaxWidth()) {
                    val columns = if (maxWidth >= 680.dp) 4 else 2
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        cards.chunked(columns).forEach { rowCards ->
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                rowCards.forEach { card -> RefundSummaryTile(card, Modifier.weight(1f)) }
                                repeat(columns - rowCards.size) { Spacer(Modifier.weight(1f)) }
                            }
                        }
                    }
                }
            }
            summary?.let { Text("Site Visit revenue ${formatRupees(it.revenuePaise)}  ·  Refunded ${formatRupees(it.refundAmountPaise)}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
            OutlinedTextField(search, { search = it.take(120) }, label = { Text("Search booking, listing, buyer or payment/refund reference") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
            Button(onClick = { if (skip == 0) refresh() else skip = 0 }, enabled = !loading, modifier = Modifier.fillMaxWidth()) { Text("Search refunds") }
            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                listOf(
                    Triple(null, "All", counts?.refundRequests),
                    Triple("pending_details", "Awaiting UPI", awaitingUpi),
                    Triple("pending", "Pending", counts?.let { (it.refundPending - awaitingUpi).coerceAtLeast(0) }),
                    Triple("refunded", "Refunded", counts?.refunded),
                    Triple("failed", "Failed", counts?.refundFailed)
                ).forEach { (key, label, count) ->
                    FilterChip(selected = filter == key, onClick = { filter = key; skip = 0 }, label = { Text(if (count == null) label else "$label ($count)") })
                }
            }
            if (loading) LinearProgressIndicator(Modifier.fillMaxWidth())
            error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            message?.let { Text(it, color = MaterialTheme.colorScheme.primary) }
            if (!loading && error == null && items.isEmpty()) Text("No Site Visit refund cases match this filter.", color = MaterialTheme.colorScheme.onSurfaceVariant)
            items.forEach { item -> SiteVisitAccountingRefundCard(item) { onRefundClick(item.bookingId) } }
            if (total > 25) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                    Text("${skip + 1}–${(skip + items.size).coerceAtMost(total)} of $total", style = MaterialTheme.typography.bodySmall)
                    Row {
                        TextButton(enabled = skip > 0 && !loading, onClick = { skip = (skip - 25).coerceAtLeast(0) }) { Text("Previous") }
                        TextButton(enabled = skip + 25 < total && !loading, onClick = { skip += 25 }) { Text("Next") }
                    }
                }
            }
        }
    }
}

private data class RefundSummaryCard(val label: String, val count: Int, val background: Color, val foreground: Color)

@Composable
private fun RefundSummaryTile(data: RefundSummaryCard, modifier: Modifier = Modifier) {
    Card(modifier, shape = androidx.compose.foundation.shape.RoundedCornerShape(16.dp), colors = CardDefaults.cardColors(containerColor = data.background), border = BorderStroke(1.dp, data.foreground.copy(alpha = .16f))) {
        Column(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 11.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
            Text(data.count.toString(), color = data.foreground, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Text(data.label, color = data.foreground, style = MaterialTheme.typography.labelMedium, maxLines = 2)
        }
    }
}

@Composable
private fun SiteVisitAccountingRefundCard(item: SiteVisitAccountingRefundDto, onClick: () -> Unit) {
    val color = refundStatusColor(item.status)
    Card(Modifier.fillMaxWidth().clickable(onClick = onClick), shape = androidx.compose.foundation.shape.RoundedCornerShape(18.dp), border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant), elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)) {
        Column(Modifier.padding(15.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                Text("Booking #${item.bookingId}  ·  Refund #${item.refundId}", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                StatusBadge(item.status.replace('_', ' '), color)
            }
            Text("${item.propertyName}  ·  ${item.listingCode ?: "Listing #${item.listingId}"}", style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.SemiBold)
            Text("Listing #${item.listingId}  ·  Buyer ${item.buyerName} (${item.buyerMobile})", style = MaterialTheme.typography.bodyMedium)
            Text("Booked ${formatSiteVisitDate(item.createdAt.take(10))}  ·  Visit ${formatSiteVisitDate(item.visitDate)} at ${formatSiteVisitTime(item.visitTime)}", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("${if (item.actualPaise != null) "Actual refund" else "Eligible refund"} ${formatRupees(item.actualPaise ?: item.eligiblePaise)}", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Text("Payment ${item.paymentStatus.replace('_', ' ')}", style = MaterialTheme.typography.labelLarge)
            }
            Text("Tap to view refund details  ›", color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.labelMedium)
        }
    }
}

private fun refundStatusColor(status: String): Color = when (siteVisitRefundStatusColorKey(status)) {
    "awaiting_upi" -> Color(0xFFB45309)
    "pending" -> Color(0xFF1D4ED8)
    "refunded" -> Color(0xFF15803D)
    "failed" -> Color(0xFFB91C1C)
    else -> Color(0xFF475569)
}

@Composable
fun AccountingSiteVisitRefundDetailScreen(bookingId: Int, onBack: () -> Unit = {}) {
    BackHandler(onBack = onBack)
    val api = ApiClient.siteVisitApi
    val scope = rememberCoroutineScope()
    var item by remember(bookingId) { mutableStateOf<SiteVisitAccountingRefundDto?>(null) }
    var loading by remember { mutableStateOf(false) }
    var processing by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var message by remember { mutableStateOf<String?>(null) }
    var amountText by remember(bookingId) { mutableStateOf("") }
    var reference by remember { mutableStateOf("") }
    var note by remember { mutableStateOf("") }
    var confirmDialog by remember { mutableStateOf(false) }
    var failureDialog by remember { mutableStateOf(false) }
    fun refresh() = scope.launch {
        loading = true; error = null
        try {
            val result = api.accountingRefunds(skip = 0, limit = 100, search = bookingId.toString())
            item = result.items.firstOrNull { it.bookingId == bookingId }
            if (item == null) error = "Refund details for booking #$bookingId were not found or are no longer available."
            else if (amountText.isBlank()) amountText = BigDecimal.valueOf(item!!.eligiblePaise.toLong(), 2).toPlainString()
        } catch (e: Exception) { error = "Could not load refund details. Check your Accounting access or connection." }
        finally { loading = false }
    }
    LaunchedEffect(bookingId) { refresh() }
    val current = item
    Scaffold { inset ->
        Column(Modifier.fillMaxSize().padding(inset).padding(16.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                Text("Refund Details", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                Row { TextButton(onClick = onBack) { Text("Back") }; TextButton(onClick = { refresh() }, enabled = !loading && !processing) { Text("Refresh") } }
            }
            if (loading) LinearProgressIndicator(Modifier.fillMaxWidth())
            error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            message?.let { Text(it, color = MaterialTheme.colorScheme.primary) }
            current?.let { refund ->
                DetailSection("Booking and visit") {
                    DetailLine("Site Visit Booking ID", "#${refund.bookingId}")
                    DetailLine("Booking date", formatSiteVisitDate(refund.createdAt.take(10)))
                    DetailLine("Visit date and time", "${formatSiteVisitDate(refund.visitDate)} · ${formatSiteVisitTime(refund.visitTime)}")
                    DetailLine("Cancellation reason", refund.cancellationReason ?: "—")
                }
                DetailSection("Listing") {
                    DetailLine("Listing ID", "#${refund.listingId}")
                    DetailLine("Listing Code", refund.listingCode ?: "Unavailable")
                    DetailLine("Property", refund.propertyName)
                }
                DetailSection("Buyer") {
                    DetailLine("Name", refund.buyerName)
                    DetailLine("Mobile", refund.buyerMobile)
                    if (canDisplaySiteVisitBuyerUpi(SessionManager.currentUserRole)) DetailLine("Buyer UPI ID", refund.buyerUpiId ?: "Awaiting buyer details")
                }
                DetailSection("Payment") {
                    DetailLine("Payment status", refund.paymentStatus.replace('_', ' '))
                    DetailLine("Booking amount", formatRupees(refund.feePaise))
                    DetailLine("Original payment reference", refund.paymentReference ?: "Unavailable")
                }
                DetailSection("Refund") {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) { Text("Status", fontWeight = FontWeight.SemiBold); StatusBadge(refund.status.replace('_', ' '), refundStatusColor(refund.status)) }
                    DetailLine("Refund ID", "#${refund.refundId}")
                    DetailLine("Eligible amount", formatRupees(refund.eligiblePaise))
                    DetailLine("Actual refunded", refund.actualPaise?.let { formatRupees(it) } ?: "Not recorded")
                    DetailLine("Transaction reference", refund.transactionReference ?: "Not recorded")
                    DetailLine("Confirmed by", refund.accountingUserId?.let { "Accounting user #$it" } ?: "Not recorded")
                    DetailLine("Confirmed at", refund.refundedAt ?: "Not recorded")
                    DetailLine("Failure reason", refund.failureReason ?: "—")
                    DetailLine("Internal note", refund.internalNote ?: "—")
                }
                if (refund.history.isNotEmpty()) DetailSection("Refund history") {
                    refund.history.forEach { event ->
                        Text("${event.action.replace('_', ' ')}  ·  ${event.actorRole} #${event.actorId}", fontWeight = FontWeight.SemiBold)
                        Text("${event.previousStatus ?: "—"} → ${event.newStatus}  ·  ${event.createdAt}", color = MaterialTheme.colorScheme.onSurfaceVariant)
                        event.note?.let { Text(it) }
                    }
                }
                if (refund.status == "pending") DetailSection("Accounting actions") {
                    OutlinedTextField(amountText, { amountText = it.filter { c -> c.isDigit() || c == '.' }.take(12) }, label = { Text("Actual amount sent (₹)") }, modifier = Modifier.fillMaxWidth(), enabled = !processing, singleLine = true)
                    OutlinedTextField(reference, { reference = it.take(120) }, label = { Text("UPI transaction/reference ID") }, modifier = Modifier.fillMaxWidth(), enabled = !processing, singleLine = true)
                    OutlinedTextField(note, { note = it.take(500) }, label = { Text("Internal note / failure reason") }, modifier = Modifier.fillMaxWidth(), enabled = !processing)
                    Button(enabled = !processing && canConfirmSiteVisitRefund(parseSiteVisitRefundAmountPaise(amountText), refund.eligiblePaise, reference), onClick = { confirmDialog = true }, modifier = Modifier.fillMaxWidth()) { Text(if (processing) "Submitting…" else "Confirm refund") }
                    TextButton(enabled = !processing && canRecordSiteVisitRefundFailure(note), onClick = { failureDialog = true }, modifier = Modifier.fillMaxWidth()) { Text("Mark refund failed") }
                    Text("Confirm only after the external refund has been completed. MyBrokerr does not transfer money.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
    if (confirmDialog && current != null) AlertDialog(
        onDismissRequest = { if (!processing) confirmDialog = false },
        title = { Text("Confirm refund") },
        text = { Text("Record ${formatRupees(parseSiteVisitRefundAmountPaise(amountText) ?: 0)} as externally refunded with reference ${reference.trim()}?") },
        confirmButton = { TextButton(enabled = !processing, onClick = {
            val paise = parseSiteVisitRefundAmountPaise(amountText) ?: return@TextButton
            processing = true; confirmDialog = false
            scope.launch {
                try {
                    val result = api.confirmRefund(current.refundId, SiteVisitRefundConfirmDto(paise, reference.trim(), note.trim().ifBlank { null }))
                    message = if (result.idempotent) "This refund confirmation was already recorded." else "Refund confirmation recorded by the server."
                    refresh()
                } catch (e: Exception) { error = accountingRefundActionError(e, "Refund confirmation could not be recorded.") }
                finally { processing = false }
            }
        }) { Text("Confirm") } },
        dismissButton = { TextButton(enabled = !processing, onClick = { confirmDialog = false }) { Text("Cancel") } }
    )
    if (failureDialog && current != null) AlertDialog(
        onDismissRequest = { if (!processing) failureDialog = false },
        title = { Text("Mark refund failed") },
        text = { Text("Record this refund as failed? The reason will be saved to the refund history.") },
        confirmButton = { TextButton(enabled = !processing, onClick = {
            processing = true; failureDialog = false
            scope.launch {
                try {
                    api.failRefund(current.refundId, SiteVisitRefundFailureDto(note.trim()))
                    message = "Refund failure recorded by the server."
                    refresh()
                } catch (e: Exception) { error = accountingRefundActionError(e, "Refund failure could not be recorded.") }
                finally { processing = false }
            }
        }) { Text("Mark failed") } },
        dismissButton = { TextButton(enabled = !processing, onClick = { failureDialog = false }) { Text("Cancel") } }
    )
}

private fun accountingRefundActionError(error: Throwable, fallback: String): String {
    val http = error as? HttpException ?: return if (error is IOException) "Could not reach the backend. Check the connection and retry." else fallback
    val detail = http.response()?.errorBody()?.let { body -> runCatching { JSONObject(body.string()).optString("detail") }.getOrNull() }
    val safe = setOf(
        "Site Visit refund not found", "Refund was already confirmed with different transaction details",
        "Refund cannot be confirmed before buyer UPI details are submitted", "Buyer refund details are missing",
        "Refund amount exceeds the eligible amount", "UPI transaction reference has already been recorded",
        "Only a pending Site Visit refund can be marked failed"
    )
    return when {
        detail != null && detail in safe -> detail
        http.code() == 401 -> "Your session expired. Sign in again and retry."
        http.code() == 403 -> "Your active Accounting account is not authorized for this refund."
        http.code() == 409 -> "The refund status changed before the action completed. Refresh and review its current status."
        http.code() == 404 -> "This refund was not found. Refresh the dashboard."
        else -> "$fallback (HTTP ${http.code()})."
    }
}

private fun formatRupees(paise: Long): String = "₹%.2f".format(paise / 100.0)
private fun formatRupees(paise: Int): String = "₹%.2f".format(paise / 100.0)

