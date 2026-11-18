package com.example.mybroker_admin.feature.admin.listings

import com.example.mybroker_admin.data.remote.dto.PropertyBookingCancellationPreviewDto
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PropertyBookingCancellationUiPolicyTest {
    @Test
    fun superAdminRoleSpellingsShowActions() {
        listOf("SUPER_ADMIN", "Super Admin", "super_admin").forEach { role ->
            assertTrue(state(role).actionsVisible)
        }
    }

    @Test
    fun nonSuperAdminDoesNotSeePrivilegedActions() {
        listOf("ADMIN", "ACCOUNTING", null).forEach { role ->
            assertFalse(state(role).actionsVisible)
        }
    }

    @Test
    fun readOnlyDetailsDoNotExposeCancellationActions() {
        assertFalse(state(readOnly = true).actionsVisible)
    }

    @Test
    fun previewLoadingKeepsSectionVisibleAndDisablesCancellation() {
        val ui = state(previewLoading = true)
        assertTrue(ui.actionsVisible)
        assertFalse(ui.cancelEnabled)
        assertEquals("Checking cancellation eligibility", ui.statusMessage)
    }

    @Test
    fun previewErrorKeepsSectionVisibleAndProvidesSafeRetryState() {
        val ui = state(previewError = "Cancellation preview failed (HTTP 503). Retry to check eligibility.")
        assertTrue(ui.actionsVisible)
        assertFalse(ui.cancelEnabled)
        assertEquals("Cancellation preview failed (HTTP 503). Retry to check eligibility.", ui.statusMessage)
    }

    @Test
    fun ineligiblePreviewKeepsSectionVisibleAndShowsBackendReason() {
        val ui = state(preview = preview(canCancel = false, reason = "No verified captured property booking payment is linked to this booking"))
        assertTrue(ui.actionsVisible)
        assertFalse(ui.cancelEnabled)
        assertEquals("No verified captured property booking payment is linked to this booking", ui.statusMessage)
    }

    @Test
    fun eligiblePreviewEnablesCancelAction() {
        val ui = state(preview = preview(canCancel = true))
        assertTrue(ui.actionsVisible)
        assertTrue(ui.cancelEnabled)
        assertFalse(state(preview = preview(canCancel = true), isSubmitting = true).cancelEnabled)
    }

    @Test
    fun refundAndNoRefundSelectionsMapToSafeAmounts() {
        assertEquals(0.0, PropertyBookingCancellationUiPolicy.amountForSubmission("NO_REFUND", "", 250.0)!!, 0.0)
        assertEquals(150.25, PropertyBookingCancellationUiPolicy.amountForSubmission("REFUND", "150.25", 250.0)!!, 0.0)
        assertEquals(null, PropertyBookingCancellationUiPolicy.amountForSubmission("REFUND", "250.01", 250.0))
    }

    private fun state(
        role: String? = "SUPER_ADMIN",
        previewLoading: Boolean = false,
        previewError: String? = null,
        preview: PropertyBookingCancellationPreviewDto? = null,
        isSubmitting: Boolean = false,
        readOnly: Boolean = false
    ) = PropertyBookingCancellationUiState(
        role = role,
        readOnly = readOnly,
        previewLoading = previewLoading,
        previewError = previewError,
        preview = preview,
        isSubmitting = isSubmitting
    )

    private fun preview(canCancel: Boolean, reason: String? = null) = PropertyBookingCancellationPreviewDto(
        booking_id = 12,
        listing_id = 34,
        listing_code = "L-34",
        property_name = "Test property",
        buyer_name = "Buyer",
        buyer_mobile = "0000000000",
        booking_status = "BOOKED",
        listing_status = "BOOKED",
        captured_payment_amount = 250.0,
        captured_at = null,
        can_cancel = canCancel,
        blocking_reason = reason
    )
}
