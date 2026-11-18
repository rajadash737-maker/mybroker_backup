package com.example.myapplication.ui.feature.common

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.Card
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.myapplication.ui.feature.buyer.utils.LandAreaPriceCalculator
import com.example.myapplication.ui.feature.buyer.utils.LandAreaPriceRow
import com.example.myapplication.ui.feature.buyer.utils.formatIndianNumber
import com.example.myapplication.ui.feature.buyer.utils.formatIndianCurrency
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.LocalTime
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale

data class BookingDetailTimelineEvent(val key: String, val at: String?)

private enum class TimelineState { COMPLETED, CURRENT, PENDING, TERMINAL }
private data class TimelineRow(val label: String, val at: String?, val state: TimelineState)

@Composable
fun BookingPropertyDetails(
    listingId: Int,
    title: String?,
    location: String?,
    city: String?,
    state: String?,
    pincode: String?,
    landType: String?,
    ownershipType: String? = null,
    ownerCategory: String? = null,
    description: String? = null,
    area: Double?,
    areaUnit: String?,
    listingStatus: String?,
    bookingStatus: String?,
    hasBooking: Boolean,
    agreedDealAmount: Double?,
    paymentStatus: String? = null,
    amountPaid: Double? = null,
    paymentDate: String? = null,
    transactionReference: String? = null,
    registryDate: String? = null,
    registryTime: String? = null,
    registryLocation: String? = null,
    boundaryInformation: String? = null,
    registryProofs: List<Pair<String, String?>> = emptyList(),
    offerEvents: List<BookingDetailTimelineEvent> = emptyList(),
    cancellationReason: String? = null,
    refundDecision: String? = null,
    refundStatus: String? = null,
    refundAmount: Double? = null,
    refundReference: String? = null,
    refundDate: String? = null
) {
    DetailCard(title = "Property Information") {
        DetailLine("Property", title)
        DetailLine("Listing ID", listingId.toString())
        DetailLine("Location", listOfNotNull(location, city, state, pincode).distinct().joinToString(", ").ifBlank { null })
        DetailLine("Land Type", humanize(landType))
        DetailLine("Ownership Type", humanize(ownershipType))
        DetailLine("Owner Category", humanize(ownerCategory))
        DetailLine("Description", description)
        DetailLine("Land Area", area?.takeIf { it > 0.0 }?.let {
            "${formatIndianNumber(it, maxFractionDigits = 4)} ${displayAreaUnit(areaUnit)}"
        })
        DetailLine("Listing Status", humanize(listingStatus))
        DetailLine("Boundary / Map", boundaryInformation)
    }

    Spacer(Modifier.height(12.dp))

    AgreedDealAmountSection(area, areaUnit, agreedDealAmount)

    Spacer(Modifier.height(12.dp))

    DetailCard(title = "Booking & Payment") {
        DetailLine("Booking Status", bookingStatus?.let(::bookingStatusLabel))
        DetailLine("Payment Status", paymentStatus?.let(::paymentStatusLabel))
        DetailLine("Amount Paid", amountPaid?.takeIf { it >= 0.0 }?.let(::formatCurrency))
        DetailLine("Payment Date", paymentDate?.takeIf(String::isNotBlank)?.let(::formatDateTime))
        DetailLine("Transaction Reference", transactionReference)
    }

    Spacer(Modifier.height(12.dp))

    DetailCard(title = "Registry Information") {
        DetailLine("Registry Status", bookingStatus?.let(::registryStatusLabel))
        DetailLine("Registry Date", registryDate?.takeIf(String::isNotBlank)?.let(::formatDateTime))
        DetailLine("Registry Time", registryTime?.takeIf(String::isNotBlank)?.let(::formatTime))
        DetailLine("Registry Location", registryLocation)
        registryProofs.forEach { (name, createdAt) ->
            DetailLine("Registry Proof", listOfNotNull(name, createdAt?.let(::formatDateTime)).joinToString(" - "))
        }
    }

    Spacer(Modifier.height(12.dp))

    val timeline = bookingTimeline(
        bookingStatus = bookingStatus,
        hasBooking = hasBooking,
        paymentStatus = paymentStatus,
        offerEvents = offerEvents,
        registryDate = registryDate,
        registryTime = registryTime
    )
    DetailCard(title = "Booking Timeline") {
        if (timeline.isEmpty()) {
            Text("No booking timeline events are available.", style = MaterialTheme.typography.bodyMedium)
        } else {
            timeline.forEachIndexed { index, item ->
                val stateLabel = when (item.state) {
                    TimelineState.COMPLETED -> "Completed"
                    TimelineState.CURRENT -> "Current"
                    TimelineState.PENDING -> "Pending"
                    TimelineState.TERMINAL -> "Terminal status"
                }
                Text("$stateLabel - ${item.label}", style = MaterialTheme.typography.titleSmall)
                item.at?.let { Text(formatDateTime(it), style = MaterialTheme.typography.bodySmall) }
                if (index < timeline.lastIndex) {
                    Spacer(Modifier.height(8.dp))
                    HorizontalDivider()
                    Spacer(Modifier.height(8.dp))
                }
            }
        }
    }

    if (listOf(cancellationReason, refundDecision, refundStatus, refundAmount?.toString(), refundReference, refundDate)
            .any { !it.isNullOrBlank() }) {
        Spacer(Modifier.height(12.dp))
        DetailCard(title = "Cancellation & Refund") {
            DetailLine("Status", bookingStatus?.takeIf { it.equals("cancelled", true) }?.let(::bookingStatusLabel))
            DetailLine("Cancellation Reason", cancellationReason)
            DetailLine("Refund Decision", humanize(refundDecision))
            DetailLine("Refund Status", humanize(refundStatus))
            DetailLine("Refund Amount", refundAmount?.let(::formatCurrency))
            DetailLine("Refund Reference", refundReference)
            DetailLine("Refund Confirmed", refundDate?.takeIf(String::isNotBlank)?.let(::formatDateTime))
        }
    }
}

@Composable
private fun AgreedDealAmountSection(area: Double?, areaUnit: String?, agreedDealAmount: Double?) {
    val breakdown = LandAreaPriceCalculator.calculateForAgreedDeal(area, areaUnit, agreedDealAmount)
    DetailCard(title = "Agreed Deal Amount") {
        Text(
            text = breakdown.totalLandAmount?.let(::formatCurrency) ?: "Unavailable",
            style = MaterialTheme.typography.headlineSmall,
            color = MaterialTheme.colorScheme.primary
        )
        Spacer(Modifier.height(4.dp))
        Text(
            "Calculated using accepted deal amount and registered land area.",
            style = MaterialTheme.typography.bodySmall
        )
        Spacer(Modifier.height(10.dp))
        AreaPriceTable(breakdown.rows)
    }
}

@Composable
private fun AreaPriceTable(rows: List<LandAreaPriceRow>) {
    val headerColor = MaterialTheme.colorScheme.secondaryContainer
    val alternateRowColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.45f)

    Row(
        Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState())
    ) {
        Column(Modifier.width(480.dp)) {
            TableRowBackground(color = headerColor) {
                TableCell("Unit", width = 100.dp, numeric = false, header = true)
                TableCell("Converted Area", width = 170.dp, numeric = true, header = true)
                TableCell("Price / Unit", width = 210.dp, numeric = true, header = true)
            }
            HorizontalDivider()

            rows.forEachIndexed { index, row ->
                val rowColor = if (index % 2 == 0) MaterialTheme.colorScheme.surface else alternateRowColor
                TableRowBackground(color = rowColor) {
                    TableCell(row.unitLabel, width = 100.dp, numeric = false)
                    TableCell(
                        row.convertedArea?.let { formatIndianNumber(it, maxFractionDigits = 4) } ?: "Unavailable",
                        width = 170.dp,
                        numeric = true
                    )
                    TableCell(
                        row.perUnitPrice?.let(::formatCurrency) ?: "Unavailable",
                        width = 210.dp,
                        numeric = true
                    )
                }
                HorizontalDivider()
            }
        }
    }
}

@Composable
private fun TableRowBackground(color: androidx.compose.ui.graphics.Color, content: @Composable RowScope.() -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .background(color)
    ) {
        content()
    }
}

@Composable
private fun TableCell(text: String, width: androidx.compose.ui.unit.Dp, numeric: Boolean, header: Boolean = false) {
    Text(
        text = text,
        modifier = Modifier
            .width(width)
            .padding(horizontal = 8.dp, vertical = 10.dp),
        style = if (header) MaterialTheme.typography.labelMedium else MaterialTheme.typography.bodySmall,
        maxLines = 1,
        softWrap = false,
        textAlign = if (numeric) androidx.compose.ui.text.style.TextAlign.End else androidx.compose.ui.text.style.TextAlign.Start
    )
}

@Composable
private fun DetailCard(title: String, content: @Composable () -> Unit) {
    Card(Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            content()
        }
    }
}

@Composable
private fun DetailLine(label: String, value: String?) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(label, Modifier.weight(0.9f), style = MaterialTheme.typography.bodyMedium)
        Text(value?.takeIf(String::isNotBlank) ?: "N/A", Modifier.weight(1.1f), style = MaterialTheme.typography.bodyMedium)
    }
}

private fun bookingTimeline(
    bookingStatus: String?,
    hasBooking: Boolean,
    paymentStatus: String?,
    offerEvents: List<BookingDetailTimelineEvent>,
    registryDate: String?,
    registryTime: String?
): List<TimelineRow> {
    val status = bookingStatus.orEmpty().trim().lowercase(Locale.ROOT)
    val cancelled = status == "cancelled"
    val bookedStates = setOf("booked", "confirmed", "in_process", "registry_scheduled", "registry_done", "sold", "cancelled")
    val bookingConfirmed = hasBooking || status in bookedStates
    val paymentCompleted = paymentStatus.equals("success", true)
    val registryScheduled = !registryDate.isNullOrBlank() || status in setOf("registry_scheduled", "registry_done", "sold")
    val registryCompleted = !cancelled && status in setOf("registry_done", "sold")
    val accepted = offerEvents.any { it.key in setOf("seller_accepted", "offer_accepted", "accepted") } ||
        status in setOf("accepted_book_now", "booked", "confirmed", "in_process", "registry_scheduled", "registry_done", "sold")
    val offerPlaced = offerEvents.firstOrNull { it.key == "offer_placed" }
    val offerAccepted = offerEvents.firstOrNull { it.key in setOf("seller_accepted", "offer_accepted", "accepted") }
    val milestones = mutableListOf<Triple<String, String?, Boolean>>()
    if (offerEvents.isNotEmpty()) {
        milestones += Triple("Offer Placed", offerPlaced?.at, offerPlaced != null || accepted)
        milestones += Triple("Offer Accepted", offerAccepted?.at, accepted)
    }
    milestones += Triple("Booking Confirmed", null, bookingConfirmed)
    milestones += Triple("Payment Completed", null, paymentCompleted)
    milestones += Triple(
        "Registry Scheduled",
        listOfNotNull(registryDate, registryTime).takeIf { it.isNotEmpty() }?.joinToString("T"),
        registryScheduled
    )
    if (!cancelled) milestones += Triple("Registry Completed", null, registryCompleted)
    val currentIndex = if (cancelled) -1 else milestones.indexOfFirst { !it.third }
    val rows = milestones.mapIndexed { index, milestone ->
        val rowState = when {
            milestone.third -> TimelineState.COMPLETED
            index == currentIndex -> TimelineState.CURRENT
            else -> TimelineState.PENDING
        }
        TimelineRow(milestone.first, milestone.second, rowState)
    }.toMutableList()
    if (cancelled) rows += TimelineRow("Cancelled", null, TimelineState.TERMINAL)
    return rows
}

private fun humanize(raw: String?): String? = raw?.trim()?.takeIf(String::isNotEmpty)?.let {
    it.split('_', '-', ' ').filter(String::isNotBlank).joinToString(" ") { part ->
        part.lowercase(Locale.ROOT).replaceFirstChar { first -> first.uppercase() }
    }
}

private fun bookingStatusLabel(raw: String): String = when (raw.trim().lowercase(Locale.ROOT)) {
    "in_process" -> "In Process"
    "accepted_book_now" -> "Booking Available"
    "booked", "confirmed" -> "Booking Confirmed"
    "registry_scheduled" -> "Registry Scheduled"
    "registry_done" -> "Registry Completed"
    "cancelled" -> "Cancelled"
    "sold" -> "Sold"
    else -> humanize(raw) ?: "N/A"
}

private fun registryStatusLabel(raw: String): String = when (raw.trim().lowercase(Locale.ROOT)) {
    "registry_done" -> "Registry Completed"
    "registry_scheduled" -> "Registry Scheduled"
    "cancelled" -> "Cancelled"
    "sold" -> "Sold"
    else -> "Not Completed"
}

private fun paymentStatusLabel(raw: String): String = when (raw.trim().lowercase(Locale.ROOT)) {
    "success", "completed", "paid" -> "Payment Completed"
    "initiated", "pending" -> "Pending"
    "failed" -> "Failed"
    else -> humanize(raw) ?: "N/A"
}

private fun displayAreaUnit(raw: String?): String = when (raw?.trim()?.lowercase(Locale.ROOT)) {
    "sqft" -> "sq.ft"
    "sqm" -> "sq.m"
    "decimal" -> "decimal"
    "acre" -> "acre"
    "hectare" -> "hectare"
    "bigha" -> "bigha"
    null, "" -> "N/A"
    else -> raw
}

private fun formatCurrency(amount: Double): String = formatIndianCurrency(amount)

private fun formatDateTime(value: String): String {
    val parsed = runCatching { OffsetDateTime.parse(value).toLocalDateTime() }.getOrNull()
        ?: runCatching { LocalDateTime.parse(value) }.getOrNull()
        ?: runCatching { LocalDate.parse(value).atStartOfDay() }.getOrNull()
        ?: return value
    return parsed.format(DateTimeFormatter.ofPattern("dd MMM yyyy, hh:mm a", Locale.ENGLISH))
}

private fun formatTime(value: String): String = runCatching {
    LocalTime.parse(value).format(DateTimeFormatter.ofPattern("hh:mm a", Locale.ENGLISH))
}.getOrDefault(value)
