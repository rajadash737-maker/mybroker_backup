package com.example.mybroker_admin.feature.sitevisit

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SiteVisitRefundUiRulesTest {
    @Test fun validatesAmountAndTransactionReference() {
        assertEquals(12550, parseSiteVisitRefundAmountPaise("125.50"))
        assertEquals(null, parseSiteVisitRefundAmountPaise("1.001"))
        assertEquals(null, parseSiteVisitRefundAmountPaise("invalid"))
        assertTrue(canConfirmSiteVisitRefund(12550, 15000, "UPI-123456"))
        assertFalse(canConfirmSiteVisitRefund(15001, 15000, "UPI-123456"))
        assertFalse(canConfirmSiteVisitRefund(100, 15000, "short"))
    }

    @Test fun validatesFailureReasonAndAccountingOnlyUpiDisplay() {
        assertTrue(canRecordSiteVisitRefundFailure("Bank rejected transfer"))
        assertFalse(canRecordSiteVisitRefundFailure("no"))
        assertTrue(canDisplaySiteVisitBuyerUpi("ACCOUNTING"))
        assertFalse(canDisplaySiteVisitBuyerUpi("ADMIN"))
        assertFalse(canDisplaySiteVisitBuyerUpi(null))
    }

    @Test fun mapsRefundStatusForConsistentBadgesAndFilters() {
        assertEquals("awaiting_upi", siteVisitRefundStatusColorKey("pending_details"))
        assertEquals("pending", siteVisitRefundStatusColorKey("pending"))
        assertEquals("refunded", siteVisitRefundStatusColorKey("refunded"))
        assertEquals("failed", siteVisitRefundStatusColorKey("failed"))
    }
}
