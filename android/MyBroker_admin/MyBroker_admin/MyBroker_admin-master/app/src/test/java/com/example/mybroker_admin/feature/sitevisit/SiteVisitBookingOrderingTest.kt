package com.example.mybroker_admin.feature.sitevisit

import com.example.mybroker_admin.core.navigation.Routes
import java.util.Locale
import org.junit.Assert.assertEquals
import org.junit.Test

class SiteVisitBookingOrderingTest {
    @Test
    fun earliestVisitDateComesFirst() {
        assertEquals(
            listOf(1, 2),
            sortSiteVisitBookings(listOf(item(2, date = "2026-11-21"), item(1, date = "2026-11-20"))).map { it.id }
        )
    }

    @Test
    fun sameDayBookingsUseAscendingTime() {
        assertEquals(
            listOf(1, 2),
            sortSiteVisitBookings(listOf(item(2, time = "15:10:00"), item(1, time = "09:05:00"))).map { it.id }
        )
    }

    @Test
    fun dateTimeUsesTwentyFourHourDisplay() {
        val previousLocale = Locale.getDefault()
        try {
            Locale.setDefault(Locale.US)
            assertEquals("20 Nov 2026 · 15:10", formatSiteVisitDateTime("2026-11-20", "15:10:00"))
            assertEquals("21 Nov 2026 · 09:05", formatSiteVisitDateTime("2026-11-21", "09:05"))
        } finally {
            Locale.setDefault(previousLocale)
        }
    }

    @Test
    fun separateDateAndTimeFormatBackendValuesAsDayMonthAnd24HourTime() {
        val previousLocale = Locale.getDefault()
        try {
            Locale.setDefault(Locale.US)
            assertEquals("20 Nov 2026", formatSiteVisitDate("2026-11-20"))
            assertEquals("15:10", formatSiteVisitTime("15:10"))
            assertEquals("09:05", formatSiteVisitTime("09:05:00"))
        } finally {
            Locale.setDefault(previousLocale)
        }
    }

    @Test
    fun separateDateAndTimeFormattersHandleInvalidAndNullValues() {
        assertEquals("Date unavailable", formatSiteVisitDate("2026-02-30"))
        assertEquals("Date unavailable", formatSiteVisitDate(null))
        assertEquals("Time unavailable", formatSiteVisitTime("25:70"))
        assertEquals("Time unavailable", formatSiteVisitTime(null))
    }

    @Test
    fun cancelledBookingsSortAfterActiveBookingsAndByVisitTime() {
        val rows = listOf(
            item(1, status = "cancelled", date = "2026-11-20"),
            item(2, status = "pending", date = "2026-11-22"),
            item(3, status = "cancelled", date = "2026-11-19")
        )
        assertEquals(listOf(2, 3, 1), sortSiteVisitBookings(rows).map { it.id })
    }

    @Test
    fun completedBookingsSortAfterActiveBookingsAndByVisitTime() {
        val rows = listOf(
            item(1, status = "completed", date = "2026-11-18"),
            item(2, status = "assigned", date = "2026-11-21"),
            item(3, status = "completed", date = "2026-11-17")
        )
        assertEquals(listOf(2, 3, 1), sortSiteVisitBookings(rows).map { it.id })
    }

    @Test
    fun allNonTerminalStatusesStayAheadOfTerminalBookings() {
        val rows = listOf("cancelled", "in_progress", "completed", "assigned", "scheduled", "pending", "correction_required")
            .mapIndexed { index, status -> item(index + 1, status = status, date = "2026-11-20") }
        assertEquals(listOf(2, 4, 5, 6, 7, 1, 3), sortSiteVisitBookings(rows).map { it.id })
    }

    @Test
    fun missingOrInvalidDateTimeSortsAfterDatedBookingsWithinEachGroup() {
        val rows = listOf(
            item(4, status = "completed", date = "bad-date"),
            item(3, status = "completed", date = "2026-11-21", time = "25:00"),
            item(2, date = "", time = ""),
            item(1, date = "2026-11-20", time = "09:05")
        )
        assertEquals(listOf(1, 2, 3, 4), sortSiteVisitBookings(rows).map { it.id })
        assertEquals("Visit time unavailable", formatSiteVisitDateTime("2026-02-30", "10:00"))
        assertEquals("Visit time unavailable", formatSiteVisitDateTime(null, null))
    }

    @Test
    fun equalTimestampsHaveDeterministicBookingIdOrder() {
        val rows = listOf(item(8), item(2), item(5))
        assertEquals(listOf(2, 5, 8), sortSiteVisitBookings(rows).map { it.id })
    }

    @Test
    fun bookingsLoadedOnLaterPagesAreSortedWithEarlierPages() {
        val firstPage = listOf(item(1, date = "2026-11-22"), item(2, date = "2026-11-24"))
        val laterPage = listOf(item(3, date = "2026-11-20"))
        val allLoadedPages = firstPage.toMutableList().apply { addAll(laterPage) }
        assertEquals(listOf(3, 1, 2), sortSiteVisitBookings(allLoadedPages).map { it.id })
        assertEquals(listOf(1, 2), firstPage.map { it.id })
    }

    @Test
    fun fieldOfficerBookingsSortActiveBeforeCompletedAndCancelled() {
        val rows = listOf(
            fieldItem(1, "cancelled", "2026-11-18"),
            fieldItem(2, "in_progress", "2026-11-21"),
            fieldItem(3, "completed", "2026-11-17"),
            fieldItem(4, "scheduled", "2026-11-20")
        )
        assertEquals(listOf(4, 2, 3, 1), sortFieldOfficerSiteVisits(rows).map { it.id })
    }

    @Test
    fun fieldOfficerBookingsSortEarliestDateAndSameDayTimeFirst() {
        val rows = listOf(
            fieldItem(1, date = "2026-11-21", time = "09:00"),
            fieldItem(2, date = "2026-11-20", time = "15:10"),
            fieldItem(3, date = "2026-11-20", time = "09:05")
        )
        assertEquals(listOf(3, 2, 1), sortFieldOfficerSiteVisits(rows).map { it.id })
    }

    @Test
    fun fieldOfficerFilterKeepsAllAndSelectsStatusesCaseInsensitively() {
        val rows = listOf(fieldItem(1, "assigned"), fieldItem(2, "scheduled"), fieldItem(3, "in_progress"))
        assertEquals(listOf(1, 2, 3), filterFieldOfficerSiteVisits(rows, "all").map { it.id })
        assertEquals(listOf(3), filterFieldOfficerSiteVisits(rows, "IN_PROGRESS").map { it.id })
    }

    @Test
    fun fieldOfficerBookingsPutInvalidTimesAfterDatedBookingsAndBreakTiesById() {
        val rows = listOf(
            fieldItem(9, "assigned", "2026-11-20", "10:00"),
            fieldItem(4, "assigned", "2026-11-20", "10:00:00"),
            fieldItem(2, "assigned", "bad-date", "10:00"),
            fieldItem(1, "assigned", "2026-11-20", "invalid")
        )
        assertEquals(listOf(4, 9, 1, 2), sortFieldOfficerSiteVisits(rows).map { it.id })
    }

    @Test
    fun fieldOfficerBookingRouteUsesTappedBookingId() {
        val tappedBookingId = 314
        assertEquals("field_site_visit_booking/314", Routes.fieldSiteVisitBookingDetail(tappedBookingId))
    }

    private fun item(
        id: Int,
        status: String = "pending",
        date: String = "2026-11-20",
        time: String = "10:00:00"
    ) = SiteVisitListItemDto(
        id = id,
        listingId = id,
        listingCode = "LST-$id",
        propertyName = "Property $id",
        buyerName = "Buyer $id",
        buyerMobile = "910000000$id",
        visitDate = date,
        visitTime = time,
        visitorCount = 1,
        status = status,
        paymentStatus = "success",
        fee = "100.00",
        paidAt = null,
        officer = null
    )

    private fun fieldItem(
        id: Int,
        status: String = "assigned",
        date: String = "2026-11-20",
        time: String = "10:00:00"
    ) = FieldOfficerVisitDto(
        id = id,
        listingId = id,
        listingCode = "LST-$id",
        propertyName = "Property $id",
        buyerName = "Buyer $id",
        buyerMobile = "910000000$id",
        visitDate = date,
        visitTime = time,
        visitorCount = 2,
        pickupAddress = "Test pickup address",
        message = null,
        status = status,
        paymentStatus = "success",
        fee = "100.00",
        startedAt = null,
        completedAt = null
    )
}
