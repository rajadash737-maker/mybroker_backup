package com.example.myapplication.ui.feature.sitevisit

import com.example.myapplication.ui.feature.sitevisit.data.SiteVisitCreateRequest
import com.example.myapplication.ui.feature.sitevisit.data.SiteVisitBookingDto
import com.example.myapplication.ui.feature.sitevisit.data.SiteVisitCancelRequest
import com.example.myapplication.ui.feature.sitevisit.data.SiteVisitApi
import com.example.myapplication.ui.feature.sitevisit.presentation.SiteVisitBookingTime
import com.example.myapplication.ui.feature.sitevisit.presentation.SiteVisitUiRules
import com.google.gson.Gson
import java.time.LocalDate
import java.time.LocalTime
import java.util.Locale
import retrofit2.http.POST
import retrofit2.http.Path
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

class SiteVisitBookingTimeTest {
    private val today = LocalDate.of(2026, 11, 16)

    @Test fun todayAndFutureDatesAreAllowedButPastDatesAreRejected() {
        assertEquals(true, SiteVisitBookingTime.isDateAllowed(today, today))
        assertEquals(true, SiteVisitBookingTime.isDateAllowed(today.plusDays(1), today))
        assertFalse(SiteVisitBookingTime.isDateAllowed(today.minusDays(1), today))
    }

    @Test fun selectorsExposeOnlyAllowedZeroPaddedValues() {
        assertEquals(listOf("09", "10", "11", "12", "13", "14", "15", "16", "17"), SiteVisitBookingTime.hours)
        assertEquals("00", SiteVisitBookingTime.minutes.first())
        assertEquals("59", SiteVisitBookingTime.minutes.last())
        assertEquals(60, SiteVisitBookingTime.minutes.size)
        assertEquals(LocalTime.of(9, 0), SiteVisitBookingTime.timeFor("09", "00"))
        assertNull(SiteVisitBookingTime.timeFor("08", "00"))
        assertNull(SiteVisitBookingTime.timeFor("09", "60"))
    }

    @Test fun rejectsPastTimeTodayAndAllowsFutureTimeToday() {
        assertNotNull(SiteVisitBookingTime.validate("2026-11-16", "09", "00", today, LocalTime.of(9, 1)))
        assertNull(SiteVisitBookingTime.validate("2026-11-16", "09", "02", today, LocalTime.of(9, 1)))
        assertNull(SiteVisitBookingTime.validate("2026-11-16", "17", "59", today, LocalTime.of(17, 58)))
        assertNotNull(SiteVisitBookingTime.validate("2026-11-16", "18", "00", today, LocalTime.NOON))
    }

    @Test fun pickerDateFormatsAsIsoAndRequestKeepsBackendFieldNamesAndFormats() {
        assertEquals("2026-11-16", SiteVisitBookingTime.formatDate(today))
        val request = SiteVisitCreateRequest(42, "2026-11-16", "09:05", 2, "123 Example Street", null, "key")
        val json = Gson().toJson(request)
        assertEquals(true, json.contains("\"preferred_visit_date\":\"2026-11-16\""))
        assertEquals(true, json.contains("\"preferred_visit_time\":\"09:05\""))
    }

    @Test fun submitRequiresEveryRequiredField() {
        assertFalse(SiteVisitUiRules.canSubmit(42, true, "", "09", "00", "1", "123 Example Street", today, LocalTime.of(8, 0)))
        assertFalse(SiteVisitUiRules.canSubmit(42, true, "2026-11-17", "09", "00", "", "123 Example Street", today, LocalTime.of(8, 0)))
        assertFalse(SiteVisitUiRules.canSubmit(42, true, "2026-11-17", "09", "00", "21", "123 Example Street", today, LocalTime.of(8, 0)))
        assertFalse(SiteVisitUiRules.canSubmit(42, true, "2026-11-17", "09", "00", "2", " ", today, LocalTime.of(8, 0)))
        assertFalse(SiteVisitUiRules.canSubmit(42, false, "2026-11-17", "09", "00", "2", "123 Example Street", today, LocalTime.of(8, 0)))
        assertEquals(true, SiteVisitUiRules.canSubmit(42, true, "2026-11-17", "09", "00", "2", "123 Example Street", today, LocalTime.of(8, 0)))
    }

    @Test fun paymentRequiresTermsAcceptanceAndEligiblePendingPaymentState() {
        val booking = booking(status = "pending_payment", paymentStatus = "initiated")
        assertFalse(SiteVisitUiRules.isPaymentEnabled(booking, termsAccepted = false, busy = false))
        assertFalse(SiteVisitUiRules.isPaymentEnabled(booking, termsAccepted = true, busy = true))
        assertEquals(true, SiteVisitUiRules.isPaymentEnabled(booking, termsAccepted = true, busy = false))
        assertFalse(SiteVisitUiRules.isPaymentEnabled(booking(status = "cancelled"), termsAccepted = true, busy = false))
    }

    @Test fun statusCardUsesReadableDeviceLocaleDateAndTimeAndBackendCancellationEligibility() {
        val booking = booking(status = "scheduled")
        assertEquals("19 November 2026", SiteVisitUiRules.displayDate(booking.visitDate, Locale.US))
        assertEquals("3:30 PM", SiteVisitUiRules.displayTime(booking.visitTime, Locale.US))
        assertEquals(true, SiteVisitUiRules.canCancel(booking))
        assertFalse(SiteVisitUiRules.canCancel(booking(status = "in_progress")))
        assertFalse(SiteVisitUiRules.canCancel(booking(status = "completed")))
    }

    @Test fun bookingSummaryContainsServerBookingDetailsInDisplayFormats() {
        assertEquals(
            listOf(
                "Sell Land — Listing ID" to "42",
                "Property" to "Green Acres",
                "Site Visit — Booking ID" to "321",
                "Visit date" to "19 November 2026",
                "Visit time" to "3:30 PM",
                "Visitors" to "2",
                "Pickup address" to "123 Example Street",
                "Site Visit fee" to "₹500.00",
                "Payment status" to "Success"
            ),
            SiteVisitUiRules.summaryDetails(booking(status = "assigned"))
        )
    }

    @Test fun sameListingPendingPaymentIsDetectedAndOffersResumePayment() {
        val pending = booking(status = "pending_payment", paymentStatus = "initiated")
        assertEquals(pending, SiteVisitUiRules.existingBookingForListing(listOf(pending), 42))
        assertEquals(true, SiteVisitUiRules.isPendingPayment(pending))
        assertEquals("Complete Payment", SiteVisitUiRules.paymentActionLabel(pending))
        assertEquals(321, SiteVisitUiRules.paymentBookingId(pending))
    }

    @Test fun pendingBookingUsesCompletePaymentEligibilityAndNeverAllowsNewCreate() {
        val pending = booking(status = "pending_payment", paymentStatus = "initiated")
        assertEquals(true, SiteVisitUiRules.isPaymentEnabled(pending, termsAccepted = true, busy = false))
        assertEquals(false, SiteVisitUiRules.canCreateForListing(true, false, pending))
        assertEquals(false, SiteVisitUiRules.canCreateForListing(false, false, null))
    }

    @Test fun paymentResumeDelegatesOrderReuseToExistingBackendEndpointAndBookingId() {
        val method = SiteVisitApi::class.java.declaredMethods.single { it.name == "createOrder" }
        assertEquals("site-visits/{bookingId}/payment-order", requireNotNull(method.getAnnotation(POST::class.java)).value)
        assertEquals("bookingId", method.parameterAnnotations[0].filterIsInstance<Path>().single().value)
        assertEquals(321, SiteVisitUiRules.paymentBookingId(booking(status = "pending_payment", paymentStatus = "failed")))
    }

    @Test fun paidBookingIsSentToStatusAndNotCreatedAgain() {
        val paid = booking(status = "assigned", paymentStatus = "success")
        assertEquals(paid, SiteVisitUiRules.existingBookingForListing(listOf(paid), 42))
        assertEquals(true, SiteVisitUiRules.shouldOpenStatus(paid))
        assertEquals(false, SiteVisitUiRules.canCreateForListing(true, false, paid))
    }

    @Test fun cancelledUnpaidBookingFollowsBackendActiveDuplicateContract() {
        val cancelled = booking(status = "cancelled", paymentStatus = "initiated")
        assertEquals(null, SiteVisitUiRules.existingBookingForListing(listOf(cancelled), 42))
        assertEquals(true, SiteVisitUiRules.canCreateForListing(true, false, null))
    }

    @Test fun cancelledPaidBookingRemainsHistoryButDoesNotBlockFreshBooking() {
        val cancelled = booking(status = "cancelled", paymentStatus = "success")
        val replacement = booking(status = "pending_payment", paymentStatus = "initiated").copy(id = 322)
        assertEquals(null, SiteVisitUiRules.existingBookingForListing(listOf(cancelled), 42))
        assertEquals(true, SiteVisitUiRules.canCreateForListing(true, false, null))
        assertEquals(replacement, SiteVisitUiRules.existingBookingForListing(listOf(replacement, cancelled), 42))
    }

    @Test fun completedBookingRemainsHistoryAndOpensNewBookingForm() {
        val completed = booking(status = "completed", paymentStatus = "success")
        assertEquals(null, SiteVisitUiRules.existingBookingForListing(listOf(completed), 42))
        assertEquals(true, SiteVisitUiRules.canCreateForListing(true, false, null))
    }

    @Test fun activeBookingTakesPrecedenceOverCompletedHistoryAndStillBlocksNewForm() {
        val active = booking(status = "in_progress", paymentStatus = "success").copy(id = 322)
        val completed = booking(status = "completed", paymentStatus = "success")
        assertEquals(active, SiteVisitUiRules.existingBookingForListing(listOf(completed, active), 42))
        assertEquals(false, SiteVisitUiRules.canCreateForListing(true, false, active))
    }

    @Test fun allBackendActiveStatusesRemainDuplicateBlockers() {
        listOf("pending_payment", "pending", "correction_required", "assigned", "scheduled", "in_progress").forEach { status ->
            val active = booking(status = status)
            assertEquals(status, active.bookingStatus)
            assertEquals(active, SiteVisitUiRules.existingBookingForListing(listOf(active), 42))
            assertEquals(false, SiteVisitUiRules.canCreateForListing(true, false, active))
        }
    }

    @Test fun statusCardUsesDistinctListingIdListingCodeAndSiteVisitBookingId() {
        val details = SiteVisitUiRules.summaryDetails(booking(status = "assigned"))
        assertEquals("42", details.first { it.first == "Sell Land — Listing ID" }.second)
        assertFalse(details.any { it.first.contains("Listing Code") })
        assertEquals("321", details.first { it.first == "Site Visit — Booking ID" }.second)
        assertEquals(false, details.any { it.first == "Booking reference" })
    }

    @Test fun failedLookupCannotFallThroughToNewBookingForm() {
        assertEquals(false, SiteVisitUiRules.canCreateForListing(lookupComplete = false, lookupFailed = true, existing = null))
        assertEquals(false, SiteVisitUiRules.canCreateForListing(lookupComplete = true, lookupFailed = true, existing = null))
    }

    @Test fun refundLabelRequiresBackendEligibilityAndKeepsUnknownNeutral() {
        assertEquals("Refund Eligibility Pending", SiteVisitUiRules.refundStatusLabel(booking("pending_payment")))
        assertEquals(
            "Refund Not Applicable",
            SiteVisitUiRules.refundStatusLabel(booking("cancelled").copy(refund = refund(eligible = false, status = null)))
        )
        assertEquals(
            "Refund Available · UPI details required",
            SiteVisitUiRules.refundStatusLabel(booking("cancelled").copy(refund = refund(eligible = true, status = "pending_details")))
        )
        assertEquals(
            "Refunded",
            SiteVisitUiRules.refundStatusLabel(booking("refunded").copy(refund = refund(eligible = true, status = "refunded")))
        )
    }

    @Test fun cancellationRefundUpiValidationMatchesBackendShape() {
        assertEquals(true, SiteVisitUiRules.isValidUpiId("buyer.name@bank"))
        assertEquals(false, SiteVisitUiRules.isValidUpiId("not-an-upi"))
        assertEquals(false, SiteVisitUiRules.isValidUpiId("@bank"))
        assertEquals(true, SiteVisitUiRules.requiresRefundUpiBeforeCancellation(
            booking("assigned").copy(paymentStatus = "success", feePaise = 50000)
        ))
        assertEquals(false, SiteVisitUiRules.requiresRefundUpiBeforeCancellation(
            booking("pending_payment", paymentStatus = "initiated")
        ))
    }

    @Test fun cancellationSerializesOnlyTheBackendSupportedReasonField() {
        assertEquals("{\"reason\":\"Schedule changed\"}", Gson().toJson(SiteVisitCancelRequest("Schedule changed")))
    }

    private fun booking(status: String, paymentStatus: String = "success") = SiteVisitBookingDto(
        id = 321,
        listingId = 42,
        listingCode = "LAND-42",
        propertyName = "Green Acres",
        buyerName = "Buyer",
        buyerMobile = "9000000000",
        visitDate = "2026-11-19",
        visitTime = "15:30:00",
        visitorCount = 2,
        pickupAddress = "123 Example Street",
        message = null,
        bookingStatus = status,
        paymentStatus = paymentStatus,
        feeRupees = "500.00",
        feePaise = 50000
    )

    private fun refund(eligible: Boolean, status: String?) = com.example.myapplication.ui.feature.sitevisit.data.SiteVisitRefundDto(
        eligible = eligible,
        eligibleAmountPaise = if (eligible) 50000 else 0,
        status = status,
        actualRefundedAmountPaise = null,
        transactionReference = null,
        refundedAt = null
    )
}
