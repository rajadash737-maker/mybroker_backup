package com.example.mybroker_admin.feature.sitevisit

import com.example.mybroker_admin.core.navigation.Routes
import java.util.TimeZone
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Test

class SiteVisitAuditUiRulesTest {
    @Test
    fun listKeepsBackendPageOrderInsteadOfSortingOnlyThatPage() {
        val backendPage = listOf(auditItem(1, "completed"), auditItem(2, "assigned"))
        assertEquals(listOf(1, 2), preserveSiteVisitAuditServerOrder(backendPage).map { it.id })
        assertEquals(listOf(1, 2), backendPage.map { it.id })
    }

    @Test
    fun statusLabelsAndActiveTerminalClassesAreReadableAndConsistent() {
        assertEquals("Correction Required", auditStatusLabel("correction_required"))
        assertEquals("In Progress", auditStatusLabel("in_progress"))
        assertEquals("Cancelled", auditStatusLabel("cancelled"))
        listOf("pending", "assigned", "scheduled", "in_progress", "correction_required")
            .forEach { assertEquals("active", auditStatusColorKey(it)) }
        listOf("completed", "cancelled").forEach { assertEquals("terminal", auditStatusColorKey(it)) }
    }

    @Test
    fun visitDateTimeUsesLocal24HourDisplayAndHandlesInvalidValues() {
        val original = TimeZone.getDefault()
        TimeZone.setDefault(TimeZone.getTimeZone("UTC"))
        try {
            assertEquals("20 Nov 2026 · 15:10", formatSiteVisitAuditVisitDateTime("2026-11-20", "15:10:00"))
            assertEquals("21 Nov 2026 · 09:05", formatSiteVisitAuditVisitDateTime("2026-11-21", "09:05"))
            assertEquals("Visit time unavailable", formatSiteVisitAuditVisitDateTime("bad-date", "99:00"))
            assertEquals("Time unavailable", formatSiteVisitAuditTimestamp("not-a-timestamp"))
        } finally {
            TimeZone.setDefault(original)
        }
    }

    @Test
    fun auditTimelineSortsChronologicallyAndPreservesDuplicateSourceRows() {
        val events = listOf(
            timeline("Workflow", "event-2", "2026-11-20T10:00:00Z", 2),
            timeline("Assignment", "event-1", "2026-11-20T09:00:00Z", 1),
            timeline("Workflow", "event-2", "2026-11-20T10:00:00Z", 2),
            timeline("Notification", "event-3", null, 4)
        )
        val sorted = sortSiteVisitAuditTimeline(events)
        assertEquals(listOf("event-1", "event-2", "event-2", "event-3"), sorted.map { it.recordId })
        assertEquals(2, sorted.count { it.recordId == "event-2" })
        assertNotNull(parseSiteVisitAuditTimestamp("2026-11-20T10:00:00+00:00"))
        assertNotNull(parseSiteVisitAuditTimestamp("2026-11-20T10:00:00.123456+00:00"))
    }

    @Test
    fun knownAuditEventsAreHumanizedButKeepTheirOriginalIdentifiers() {
        assertEquals("Visit completed", humanizeSiteVisitAuditEvent("SITE_VISIT_COMPLETED"))
        assertEquals("Correction requested", humanizeSiteVisitAuditEvent("SITE_VISIT_CORRECTION_REQUESTED"))
        assertFalse(humanizeSiteVisitAuditEvent("SITE_VISIT_ASSIGNED").contains("SITE_VISIT_"))
    }

    @Test
    fun auditDetailRouteUsesTheTappedBookingId() {
        assertEquals("super_admin_site_visit_audit/246", Routes.superAdminSiteVisitAuditDetail(246))
    }

    private fun timeline(source: String, id: String, occurredAt: String?, sourceOrder: Int) =
        SiteVisitAuditTimelineEvent(source, id, occurredAt, "Event", "RAW_EVENT", null, null, sourceOrder = sourceOrder)

    private fun auditItem(id: Int, status: String) = SiteVisitAuditItemDto(
        id = id,
        listingId = id,
        listingCode = "L-$id",
        propertyName = "Property $id",
        buyerName = "Buyer $id",
        buyerMobile = "900000000$id",
        visitDate = "2026-11-20",
        visitTime = "10:00:00",
        visitorCount = 1,
        status = status,
        paymentStatus = "success",
        fee = "100.00",
        sellerName = "Seller",
        paymentOrderId = null,
        paymentId = null,
        paidAt = null,
        createdAt = "2026-11-19T10:00:00Z",
        officer = null
    )
}
