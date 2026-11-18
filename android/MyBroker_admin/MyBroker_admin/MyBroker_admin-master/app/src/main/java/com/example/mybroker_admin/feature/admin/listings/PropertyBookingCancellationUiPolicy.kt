package com.example.mybroker_admin.feature.admin.listings

import com.example.mybroker_admin.data.remote.dto.PropertyBookingCancellationPreviewDto
import java.util.Locale

data class PropertyBookingCancellationUiState(
    val role: String?,
    val readOnly: Boolean,
    val previewLoading: Boolean,
    val previewError: String?,
    val preview: PropertyBookingCancellationPreviewDto?,
    val isSubmitting: Boolean
) {
    val actionsVisible: Boolean
        get() = PropertyBookingCancellationUiPolicy.isSuperAdmin(role) && !readOnly

    val cancelEnabled: Boolean
        get() = actionsVisible && !previewLoading && !isSubmitting && preview?.can_cancel == true

    val statusMessage: String?
        get() = when {
            previewLoading -> "Checking cancellation eligibility"
            previewError != null -> previewError
            preview != null && !preview.can_cancel -> preview.blocking_reason
                ?: "This booking is not eligible for cancellation."
            else -> null
        }
}

object PropertyBookingCancellationUiPolicy {
    fun normalizeRole(role: String?): String? = role
        ?.trim()
        ?.replace(' ', '_')
        ?.replace('-', '_')
        ?.uppercase(Locale.ROOT)
        ?.takeIf { it.isNotEmpty() }

    fun isSuperAdmin(role: String?): Boolean = normalizeRole(role) == "SUPER_ADMIN"

    fun amountForSubmission(decision: String, amountText: String, capturedAmount: Double?): Double? {
        if (decision.equals("NO_REFUND", ignoreCase = true)) return 0.0
        val amount = amountText.trim()
            .takeIf { Regex("^\\d+(\\.\\d{1,2})?$").matches(it) }
            ?.toDoubleOrNull()
            ?: return null
        val maximumRefund = capturedAmount ?: return null
        return amount.takeIf { it > 0.0 && it <= maximumRefund }
    }
}
