package com.example.myapplication.ui.feature.sell_land.model

import com.google.gson.annotations.SerializedName

data class SellLandTrackingCardResponse(
    @SerializedName("id") val id: Int,
    @SerializedName("listing_code") val listingCode: String? = null,
    @SerializedName("title") val title: String? = null,
    @SerializedName("area") val area: Double? = null,
    @SerializedName("area_unit") val areaUnit: String,
    @SerializedName("expected_price") val expectedPrice: Double? = null,
    @SerializedName("status") val status: String,
    @SerializedName("is_draft") val isDraft: Boolean,
    @SerializedName("payment_status") val paymentStatus: String,
    @SerializedName("rejection_reason") val rejectionReason: String? = null,
    @SerializedName("field_officer_rejection_reason") val fieldOfficerRejectionReason: String? = null,
    @SerializedName("status_before_cancellation") val statusBeforeCancellation: String? = null,
    @SerializedName("cancellation_reason") val cancellationReason: String? = null,
    @SerializedName("refund_upi_id") val refundUpiId: String? = null,
    @SerializedName("refund_due_at") val refundDueAt: String? = null,
    @SerializedName("cancellation_requires_admin_review") val cancellationRequiresAdminReview: Boolean = false,
    @SerializedName("refund_forwarded_to_accounting_by_id") val refundForwardedToAccountingById: Int? = null,
    @SerializedName("refund_forwarded_to_accounting_at") val refundForwardedToAccountingAt: String? = null,
    @SerializedName("can_cancel_listing") val canCancelListing: Boolean = false,
    @SerializedName("likes_count") val likesCount: Int = 0,
    @SerializedName("offer_count") val offerCount: Int = 0,
    @SerializedName("deal_amount") val dealAmount: Double? = null,
    @SerializedName("booking_status") val bookingStatus: String? = null,
    @SerializedName("registry_date") val registryDate: String? = null,
    @SerializedName("registry_time") val registryTime: String? = null,
    @SerializedName("registry_location") val registryLocation: String? = null,
    @SerializedName("registry_proofs") val registryProofs: List<RegistryProofDto> = emptyList(),
    @SerializedName("tracking") val tracking: TrackingDto? = null,
    @SerializedName("updated_at") val updatedAt: String
)
