package com.example.mybroker_admin.feature.sitevisit

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.mybroker_admin.data.remote.ApiClient
import kotlinx.coroutines.launch

private const val AUDIT_PAGE_SIZE = 25

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SiteVisitAuditScreen(
    refreshKey: Int = 0,
    onBack: () -> Unit = {},
    onOpenBooking: (Int) -> Unit = {}
) {
    val scope = rememberCoroutineScope()
    var summary by remember { mutableStateOf<SiteVisitAuditSummaryDto?>(null) }
    var result by remember { mutableStateOf<SiteVisitAuditListDto?>(null) }
    var bookingIdText by rememberSaveable { mutableStateOf("") }
    var listingCode by rememberSaveable { mutableStateOf("") }
    var buyerSearch by rememberSaveable { mutableStateOf("") }
    var paymentReference by rememberSaveable { mutableStateOf("") }
    var listingIdText by rememberSaveable { mutableStateOf("") }
    var officerIdText by rememberSaveable { mutableStateOf("") }
    var officerSearch by rememberSaveable { mutableStateOf("") }
    var adminIdText by rememberSaveable { mutableStateOf("") }
    var accountingIdText by rememberSaveable { mutableStateOf("") }
    var dateFrom by rememberSaveable { mutableStateOf("") }
    var dateTo by rememberSaveable { mutableStateOf("") }
    var appliedFiltersText by rememberSaveable { mutableStateOf("") }
    val appliedFilters = appliedFiltersText.split('\n').filter(String::isNotBlank)
    var filtersExpanded by rememberSaveable { mutableStateOf(true) }
    var page by rememberSaveable { mutableStateOf(0) }
    var error by remember { mutableStateOf<String?>(null) }
    var loading by remember { mutableStateOf(false) }

    fun currentFilterLabels(): List<String> = buildList {
        bookingIdText.toIntOrNull()?.let { add("Booking #$it") }
        listingIdText.toIntOrNull()?.let { add("Listing #$it") }
        listingCode.takeIf(String::isNotBlank)?.let { add("Code: $it") }
        buyerSearch.takeIf(String::isNotBlank)?.let { add("Buyer: $it") }
        paymentReference.takeIf(String::isNotBlank)?.let { add("Reference: $it") }
        officerSearch.takeIf(String::isNotBlank)?.let { add("Officer: $it") }
        officerIdText.toIntOrNull()?.let { add("Officer ID: $it") }
        adminIdText.toIntOrNull()?.let { add("Admin ID: $it") }
        accountingIdText.toIntOrNull()?.let { add("Accounting ID: $it") }
        dateFrom.takeIf(String::isNotBlank)?.let { add("From $it") }
        dateTo.takeIf(String::isNotBlank)?.let { add("To $it") }
    }

    fun refresh(nextPage: Int = page, recordFilters: Boolean = false) {
        if (loading) return
        loading = true
        error = null
        if (recordFilters) appliedFiltersText = currentFilterLabels().joinToString("\n")
        scope.launch {
            try {
                val api = ApiClient.siteVisitApi
                val newSummary = api.auditSummary()
                val newResult = api.auditBookings(
                    skip = nextPage * AUDIT_PAGE_SIZE,
                    limit = AUDIT_PAGE_SIZE,
                    bookingId = bookingIdText.toIntOrNull(),
                    listingId = listingIdText.toIntOrNull(),
                    listingCode = listingCode.trim().takeIf(String::isNotEmpty),
                    buyer = buyerSearch.trim().takeIf(String::isNotEmpty),
                    reference = paymentReference.trim().takeIf(String::isNotEmpty),
                    officerId = officerIdText.toIntOrNull(),
                    officerSearch = officerSearch.trim().takeIf(String::isNotEmpty),
                    adminId = adminIdText.toIntOrNull(),
                    accountingId = accountingIdText.toIntOrNull(),
                    dateFrom = dateFrom.trim().takeIf(String::isNotEmpty),
                    dateTo = dateTo.trim().takeIf(String::isNotEmpty)
                )
                summary = newSummary
                result = newResult.copy(items = preserveSiteVisitAuditServerOrder(newResult.items))
                page = nextPage
            } catch (_: Exception) {
                error = "Could not load Site Visit audit data. Check your Super Admin access or connection."
            } finally {
                loading = false
            }
        }
    }

    LaunchedEffect(refreshKey) { refresh(recordFilters = true) }
    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Site Visit Audit", fontWeight = FontWeight.Bold)
                        Text("Read-only organization overview", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                },
                navigationIcon = { TextButton(onClick = onBack) { Text("Back") } },
                actions = { TextButton(onClick = { refresh(recordFilters = true) }, enabled = !loading) { Text("Refresh") } }
            )
        }
    ) { pad ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(pad),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 14.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            summary?.let { auditSummary ->
                item(key = "audit_metrics") {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("Organization overview", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                        val metrics = auditSummaryMetrics(auditSummary)
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            metrics.chunked(2).forEach { row ->
                                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    row.forEach { metric -> AuditMetricCard(metric, Modifier.weight(1f)) }
                                    if (row.size == 1) Spacer(Modifier.weight(1f))
                                }
                            }
                        }
                    }
                }
            }
            item(key = "audit_filters") {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(18.dp),
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                            Column(Modifier.weight(1f)) {
                                Text("Search & Filters", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                                Text(if (filtersExpanded) "Filter audit records" else "${appliedFilters.size} applied", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                            }
                            TextButton(onClick = { filtersExpanded = !filtersExpanded }) { Text(if (filtersExpanded) "Hide" else "Show") }
                        }
                        if (filtersExpanded) {
                            OutlinedTextField(bookingIdText, { bookingIdText = it.filter(Char::isDigit).take(10) }, Modifier.fillMaxWidth(), label = { Text("Booking ID") }, singleLine = true)
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                OutlinedTextField(listingIdText, { listingIdText = it.filter(Char::isDigit).take(10) }, Modifier.weight(1f), label = { Text("Listing ID") }, singleLine = true)
                                OutlinedTextField(listingCode, { listingCode = it.take(80) }, Modifier.weight(1f), label = { Text("Listing code") }, singleLine = true)
                            }
                            OutlinedTextField(buyerSearch, { buyerSearch = it.take(120) }, Modifier.fillMaxWidth(), label = { Text("Buyer name or mobile") }, singleLine = true)
                            OutlinedTextField(paymentReference, { paymentReference = it.take(120) }, Modifier.fillMaxWidth(), label = { Text("Payment or refund reference") }, singleLine = true)
                            OutlinedTextField(officerSearch, { officerSearch = it.take(120) }, Modifier.fillMaxWidth(), label = { Text("Field Officer name or mobile") }, singleLine = true)
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                OutlinedTextField(dateFrom, { dateFrom = it.take(10) }, Modifier.weight(1f), label = { Text("From date (YYYY-MM-DD)") }, singleLine = true)
                                OutlinedTextField(dateTo, { dateTo = it.take(10) }, Modifier.weight(1f), label = { Text("To date (YYYY-MM-DD)") }, singleLine = true)
                            }
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                OutlinedTextField(officerIdText, { officerIdText = it.filter(Char::isDigit).take(10) }, Modifier.weight(1f), label = { Text("Officer ID") }, singleLine = true)
                                OutlinedTextField(adminIdText, { adminIdText = it.filter(Char::isDigit).take(10) }, Modifier.weight(1f), label = { Text("Admin ID") }, singleLine = true)
                                OutlinedTextField(accountingIdText, { accountingIdText = it.filter(Char::isDigit).take(10) }, Modifier.weight(1f), label = { Text("Accounting ID") }, singleLine = true)
                            }
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                Button(onClick = { refresh(0, recordFilters = true) }, enabled = !loading, modifier = Modifier.weight(1f)) {
                                    if (loading) CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp) else Text("Search")
                                }
                                TextButton(onClick = {
                                    bookingIdText = ""; listingCode = ""; buyerSearch = ""; paymentReference = ""
                                    listingIdText = ""; officerIdText = ""; officerSearch = ""; adminIdText = ""
                                    accountingIdText = ""; dateFrom = ""; dateTo = ""; page = 0
                                    appliedFiltersText = ""
                                    refresh(0)
                                }, enabled = !loading) { Text("Clear filters") }
                            }
                        }
                        if (appliedFilters.isNotEmpty()) {
                            Text("Applied filters", style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.SemiBold)
                            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                appliedFilters.forEach { FilterChip(selected = true, onClick = {}, label = { Text(it, maxLines = 1) }) }
                            }
                        }
                    }
                }
            }
            if (loading) item(key = "audit_loading") { LinearProgressIndicator(Modifier.fillMaxWidth()) }
            error?.let { message -> item(key = "audit_error") { Text(message, color = MaterialTheme.colorScheme.error) } }
            val bookings = result?.items.orEmpty()
            if (!loading && error == null && bookings.isEmpty()) item(key = "audit_empty") {
                Text("No Site Visit bookings match the applied filters.", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            items(bookings, key = { it.id }) { booking -> AuditBookingCard(booking) { onOpenBooking(booking.id) } }
            if ((result?.total ?: 0) > AUDIT_PAGE_SIZE) item(key = "audit_pagination") {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Text("${result?.total ?: 0} records · page ${page + 1}", style = MaterialTheme.typography.bodySmall)
                    Row {
                        TextButton(onClick = { refresh(page - 1) }, enabled = page > 0 && !loading) { Text("Previous") }
                        TextButton(onClick = { refresh(page + 1) }, enabled = (page + 1) * AUDIT_PAGE_SIZE < (result?.total ?: 0) && !loading) { Text("Next") }
                    }
                }
            }
        }
    }
}

private data class AuditMetric(
    val title: String,
    val firstLabel: String,
    val firstValue: String,
    val secondLabel: String? = null,
    val secondValue: String? = null,
    val tint: Color
)

private fun auditSummaryMetrics(value: SiteVisitAuditSummaryDto): List<AuditMetric> = listOf(
    AuditMetric("Bookings", "Total", value.totalBookings.toString(), tint = Color(0xFF2563EB)),
    AuditMetric("Payment", "Paid", value.paidBookings.toString(), "Unpaid", value.unpaidBookings.toString(), Color(0xFF0F766E)),
    AuditMetric("Review", "Pending", value.pendingAdminReview.toString(), "Correction", value.correctionRequests.toString(), Color(0xFF7C3AED)),
    AuditMetric("Assignments", "Assigned", value.assigned.toString(), "Active", value.inProgress.toString(), Color(0xFF0891B2)),
    AuditMetric("Outcomes", "Completed", value.completed.toString(), "Cancelled", value.cancelled.toString(), Color(0xFF15803D)),
    AuditMetric("Refunds", "Pending", value.refundPending.toString(), "Failed", value.failedRefunds.toString(), Color(0xFFB45309)),
    AuditMetric("Refunded amount", "Total", "₹%.2f".format(value.refundedAmountPaise / 100.0), tint = Color(0xFF047857)),
    AuditMetric("Notifications", "Events", value.notificationEvents.toString(), tint = Color(0xFF475569))
)

@Composable
private fun AuditMetricCard(metric: AuditMetric, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier.heightIn(min = 112.dp),
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, metric.tint.copy(alpha = .2f)),
        colors = CardDefaults.cardColors(containerColor = metric.tint.copy(alpha = .07f))
    ) {
        Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
            Text(metric.title, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.SemiBold, color = metric.tint)
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Bottom) {
                Column(Modifier.weight(1f)) {
                    Text(metric.firstValue, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, color = metric.tint, maxLines = 1)
                    Text(metric.firstLabel, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                if (metric.secondValue != null && metric.secondLabel != null) Column(horizontalAlignment = Alignment.End) {
                    Text(metric.secondValue, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, color = metric.tint, maxLines = 1)
                    Text(metric.secondLabel, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}

@Composable
private fun AuditBookingCard(item: SiteVisitAuditItemDto, onClick: () -> Unit) {
    val tint = auditStatusTint(item.status)
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(Modifier.padding(15.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text("Site Visit #${item.id}", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                AuditStatusBadge(auditStatusLabel(item.status), tint)
            }
            Text(item.propertyName, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
            Text("Listing #${item.listingId} · ${item.listingCode ?: "Code unavailable"}", style = MaterialTheme.typography.bodyMedium)
            Text("Buyer: ${item.buyerName} · ${item.buyerMobile}", style = MaterialTheme.typography.bodyMedium)
            Surface(shape = RoundedCornerShape(12.dp), color = Color(0xFFEAF2FF)) {
                Text(formatSiteVisitAuditVisitDateTime(item.visitDate, item.visitTime), Modifier.padding(horizontal = 11.dp, vertical = 7.dp), color = Color(0xFF1D4ED8), fontWeight = FontWeight.Bold, style = MaterialTheme.typography.labelLarge)
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("Booked ${formatSiteVisitAuditTimestamp(item.createdAt)}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text("Payment ${item.paymentStatus.replace('_', ' ')}", style = MaterialTheme.typography.labelLarge)
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("Fee ₹${item.fee}", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
                Text(item.officer?.fullname?.takeIf(String::isNotBlank)?.let { "Officer: $it" } ?: "Unassigned", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Text("Tap to open audit details  ›", color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.labelMedium)
        }
    }
}

private fun auditStatusTint(status: String): Color = when (auditStatusColorKey(status)) {
    "active" -> Color(0xFF1D4ED8)
    "terminal" -> if (status.equals("completed", true)) Color(0xFF15803D) else Color(0xFFB91C1C)
    else -> Color(0xFF475569)
}

@Composable
private fun AuditStatusBadge(label: String, tint: Color) {
    Surface(shape = RoundedCornerShape(50), color = tint.copy(alpha = .12f)) {
        Text(label, Modifier.padding(horizontal = 10.dp, vertical = 5.dp), color = tint, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SiteVisitAuditDetailScreen(bookingId: Int, onBack: () -> Unit = {}) {
    BackHandler(onBack = onBack)
    val scope = rememberCoroutineScope()
    var detail by remember(bookingId) { mutableStateOf<SiteVisitAuditDetailDto?>(null) }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    fun refresh() {
        if (loading) return
        loading = true
        error = null
        scope.launch {
            try {
                detail = ApiClient.siteVisitApi.auditDetail(bookingId)
            } catch (_: Exception) {
                error = "Could not load this audit record. Check your Super Admin access or connection."
            } finally { loading = false }
        }
    }
    LaunchedEffect(bookingId) { refresh() }
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Booking #$bookingId audit", fontWeight = FontWeight.Bold) },
                navigationIcon = { TextButton(onClick = onBack) { Text("Back") } },
                actions = { TextButton(onClick = { refresh() }, enabled = !loading) { Text("Refresh") } }
            )
        }
    ) { pad ->
        Column(Modifier.fillMaxSize().padding(pad).verticalScroll(rememberScrollState()).padding(horizontal = 16.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            if (loading) LinearProgressIndicator(Modifier.fillMaxWidth())
            error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            detail?.let { booking ->
                AuditDetailSection("Booking Information") {
                    AuditDetailLine("Booking ID", "#${booking.id}")
                    AuditDetailLine("Property", booking.propertyName)
                    AuditDetailLine("Listing", "#${booking.listingId} · ${booking.listingCode ?: "Code unavailable"}")
                    AuditDetailLine("Visit", formatSiteVisitAuditVisitDateTime(booking.visitDate, booking.visitTime))
                    AuditDetailLine("Visitor count", booking.visitorCount.toString())
                    AuditDetailLine("Booking created", formatSiteVisitAuditTimestamp(booking.createdAt))
                    AuditDetailLine("Pickup address", booking.pickupAddress)
                    AuditDetailLine("Additional message", booking.message?.takeIf(String::isNotBlank) ?: "—")
                    AuditDetailLine("Site Visit fee", "₹${booking.fee}")
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Text("Current status", style = MaterialTheme.typography.labelLarge)
                        AuditStatusBadge(auditStatusLabel(booking.status), auditStatusTint(booking.status))
                    }
                    AuditDetailLine("Cancellation", booking.cancellationReason ?: "—")
                    AuditDetailLine("Cancellation actor role", booking.cancellationActorRole ?: "—")
                }
                AuditDetailSection("Buyer Information") {
                    AuditDetailLine("Buyer", booking.buyerName)
                    AuditDetailLine("Mobile", booking.buyerMobile)
                }
                AuditDetailSection("Payment Information") {
                    AuditDetailLine("Payment status", booking.paymentStatus.replace('_', ' '))
                    AuditDetailLine("Payment amount", "₹${booking.fee}")
                    AuditDetailLine("Payment ID", booking.paymentId ?: "Unavailable")
                    AuditDetailLine("Payment order ID", booking.paymentOrderId ?: "Unavailable")
                    AuditDetailLine("Paid at", formatSiteVisitAuditTimestamp(booking.paidAt))
                }
                AuditDetailSection("Assignment Information") {
                    AuditDetailLine("Current Field Officer", booking.officer?.let { "${it.fullname ?: "Officer"} · #${it.id}" } ?: "Unassigned")
                    AuditDetailLine("Admin owner", "Not returned by the Super Admin audit detail API")
                    AuditDetailLine("Assignment events", booking.assignmentHistory.size.toString())
                }
                AuditDetailSection("Workflow Timeline") {
                    val events = siteVisitAuditWorkflowTimeline(booking)
                    if (events.isEmpty()) Text("No workflow history was returned.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    events.forEachIndexed { index, event -> AuditTimelineRow(event, isLast = index == events.lastIndex) }
                }
                AuditDetailSection("Refund Information") {
                    val refundEvents = siteVisitAuditRefundTimeline(booking)
                    if (refundEvents.isEmpty()) Text("No refund history was returned.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    refundEvents.forEachIndexed { index, event -> AuditTimelineRow(event, isLast = index == refundEvents.lastIndex) }
                    if (refundEvents.isNotEmpty()) AuditDetailLine("Latest refund status", refundEvents.last().facts.firstOrNull { it.startsWith("Status:") }?.removePrefix("Status: ") ?: "See history")
                }
                AuditDetailSection("Notification History") {
                    val events = siteVisitAuditNotificationTimeline(booking)
                    if (events.isEmpty()) Text("No notification history was returned.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    events.forEachIndexed { index, event -> AuditTimelineRow(event, isLast = index == events.lastIndex) }
                    Text("The API returns notification records and read state; it does not return delivery attempts or delivery errors.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Text("Audit is read-only. No booking changes can be made here.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
private fun AuditDetailSection(title: String, content: @Composable () -> Unit) {
    Card(Modifier.fillMaxWidth(), shape = RoundedCornerShape(18.dp), border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)) {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            content()
        }
    }
}

@Composable
private fun AuditDetailLine(label: String, value: String) {
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, style = MaterialTheme.typography.bodyLarge)
    }
}

@Composable
private fun AuditTimelineRow(event: SiteVisitAuditTimelineEvent, isLast: Boolean) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Surface(Modifier.size(11.dp), shape = RoundedCornerShape(50), color = timelineSourceTint(event.source)) {}
            if (!isLast) Spacer(Modifier.width(2.dp).height(44.dp))
        }
        Column(Modifier.weight(1f).padding(bottom = if (isLast) 0.dp else 8.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Top) {
                Text(event.title, Modifier.weight(1f), style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.SemiBold)
                Text(formatSiteVisitAuditTimestamp(event.occurredAt), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Text("${event.source}${event.recordId?.let { " · record #$it" } ?: ""}", style = MaterialTheme.typography.labelMedium, color = timelineSourceTint(event.source), fontWeight = FontWeight.SemiBold)
            event.originalEvent?.let { Text("Original event: $it", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
            event.occurredAt?.let { Text("Source timestamp: $it", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
            event.actor?.let { Text("Actor / recipient: $it", style = MaterialTheme.typography.bodySmall) }
            event.reason?.let { Text("Reason / note: $it", style = MaterialTheme.typography.bodySmall) }
            event.facts.forEach { Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
        }
    }
}

private fun timelineSourceTint(source: String): Color = when (source) {
    "Payment" -> Color(0xFF0F766E)
    "Assignment" -> Color(0xFF2563EB)
    "Workflow" -> Color(0xFF7C3AED)
    "Refund" -> Color(0xFFB45309)
    else -> Color(0xFF475569)
}
