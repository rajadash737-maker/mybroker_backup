package com.example.myapplication.ui.feature.sitevisit.presentation

import com.example.myapplication.ui.feature.sitevisit.data.SiteVisitBookingDto
import java.time.LocalDate
import java.time.LocalTime
import java.time.format.DateTimeFormatter
import java.util.Locale

internal object SiteVisitUiRules {
    private val cancellableStatuses = setOf("pending_payment", "pending", "correction_required", "assigned", "scheduled")
    private val activeBookingStatuses = setOf("pending_payment", "pending", "correction_required", "assigned", "scheduled", "in_progress")
    private val progressStatuses = listOf("pending_payment", "pending", "assigned", "scheduled", "in_progress", "completed")

    fun canCancel(booking: SiteVisitBookingDto): Boolean = booking.bookingStatus.lowercase() in cancellableStatuses

    fun isPaymentEnabled(booking: SiteVisitBookingDto, termsAccepted: Boolean, busy: Boolean): Boolean =
        termsAccepted && !busy && booking.bookingStatus == "pending_payment" && booking.paymentStatus in setOf("initiated", "failed")

    /** Completed and cancelled visits remain in history, but only active states block a new request. */
    fun existingBookingForListing(bookings: List<SiteVisitBookingDto>, listingId: Int): SiteVisitBookingDto? {
        if (listingId <= 0) return null
        return bookings.firstOrNull {
            it.listingId == listingId && it.bookingStatus.lowercase() in activeBookingStatuses
        }
    }

    fun isPendingPayment(booking: SiteVisitBookingDto): Boolean =
        booking.bookingStatus.equals("pending_payment", ignoreCase = true) &&
            booking.paymentStatus.lowercase() in setOf("initiated", "failed")

    fun paymentActionLabel(booking: SiteVisitBookingDto): String =
        if (isPendingPayment(booking)) "Complete Payment" else "Continue to Payment"

    fun canCreateForListing(lookupComplete: Boolean, lookupFailed: Boolean, existing: SiteVisitBookingDto?): Boolean =
        lookupComplete && !lookupFailed && existing == null

    fun paymentBookingId(booking: SiteVisitBookingDto): Int? =
        booking.id.takeIf { isPendingPayment(booking) }

    fun shouldOpenStatus(booking: SiteVisitBookingDto?): Boolean = booking != null && !isPendingPayment(booking)

    fun canSubmit(
        listingId: Int,
        feeLoaded: Boolean,
        date: String,
        hour: String?,
        minute: String?,
        visitors: String,
        address: String,
        today: LocalDate,
        now: LocalTime
    ): Boolean {
        if (listingId <= 0 || !feeLoaded || SiteVisitBookingTime.validate(date, hour, minute, today, now) != null) return false
        val count = visitors.toIntOrNull() ?: return false
        return count in 1..20 && address.trim().length in 10..1000
    }

    fun displayDate(isoDate: String, locale: Locale = Locale.getDefault()): String = runCatching {
        LocalDate.parse(isoDate).format(DateTimeFormatter.ofPattern("d MMMM yyyy", locale))
    }.getOrDefault("Date unavailable")

    fun displayTime(isoTime: String, locale: Locale = Locale.getDefault()): String = runCatching {
        LocalTime.parse(isoTime).format(DateTimeFormatter.ofPattern("h:mm a", locale))
    }.getOrDefault("Time unavailable")

    fun progressIndex(status: String): Int = progressStatuses.indexOf(status.lowercase())
    fun progressFraction(status: String): Float = ((progressIndex(status) + 1).toFloat() / progressStatuses.size).coerceIn(0f, 1f)
    fun progressLabels(): List<String> = listOf("Payment", "Pending", "Assigned", "Scheduled", "In progress", "Completed")

    fun summaryDetails(booking: SiteVisitBookingDto): List<Pair<String, String>> = listOf(
        "Sell Land — Listing ID" to booking.listingId.toString(),
        "Property" to booking.propertyName,
        "Site Visit — Booking ID" to booking.id.toString(),
        "Visit date" to displayDate(booking.visitDate),
        "Visit time" to displayTime(booking.visitTime),
        "Visitors" to booking.visitorCount.toString(),
        "Pickup address" to booking.pickupAddress,
        "Site Visit fee" to "₹${booking.feeRupees}",
        "Payment status" to booking.paymentStatus.replace('_', ' ').replaceFirstChar { it.uppercase() }
    )

    fun refundStatusLabel(booking: SiteVisitBookingDto): String {
        val refund = booking.refund ?: return "Refund Eligibility Pending"
        if (!refund.eligible) return "Refund Not Applicable"
        return when (refund.status?.lowercase()) {
            "refunded" -> "Refunded"
            "failed" -> "Refund Failed"
            "pending" -> "Refund Processing"
            "pending_details" -> "Refund Available · UPI details required"
            else -> "Refund Available"
        }
    }

    fun requiresRefundUpiBeforeCancellation(booking: SiteVisitBookingDto): Boolean =
        booking.paymentStatus.equals("success", ignoreCase = true) && booking.feePaise > 0

    fun isValidUpiId(value: String): Boolean =
        Regex("^[A-Za-z0-9._-]{2,80}@[A-Za-z0-9.-]{2,40}$").matches(value.trim())
}
