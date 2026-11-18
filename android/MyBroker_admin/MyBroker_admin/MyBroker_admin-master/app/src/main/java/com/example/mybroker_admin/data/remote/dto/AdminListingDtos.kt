package com.example.mybroker_admin.data.remote.dto

import com.google.gson.Gson
import com.google.gson.annotations.JsonAdapter
import com.google.gson.JsonElement
import com.google.gson.TypeAdapter
import com.google.gson.stream.JsonReader
import com.google.gson.stream.JsonWriter

data class AdminListingListResponseDto(
    val total: Int,
    val skip: Int,
    val limit: Int,
    val items: List<AdminListingItemDto>
)

data class AdminListingItemDto(
    val id: Int,
    val listing_code: String?,
    val title: String?,
    val owner_name: String?,
    val owner_mobile: String?,
    val ownership_type: String?, // added
    val city: String?,
    val state: String?,
    val expected_price: Double?,
    val status: String
)

data class AdminListingDetailDto(
    val id: Int,
    val title: String?,
    val instagram_url: String? = null,
    val owner_name: String?,
    val owner_mobile: String?,
    val owner_category: String? = null,
    val ownership_type: String?, // added
    val land_type: String?,
    val area: Double?,
    val area_unit: String?,
    val city: String?,
    val state: String?,
    val pincode: String?,
    val price_type: String?,
    val expected_price: Double?,
    val negotiable: Boolean,
    val payment_status: String? = null,
    val payment_paid_at: String? = null,
    val payment_amount: Double? = null,
    val status: String,
    val rejection_reason: String?,
    val reviewed_by_id: Int? = null,
    val reviewed_at: String? = null,
    val created_at: String? = null,
    val admin_handler: AdminCaseLockOfficerSummaryDto? = null,
    val field_officer: AdminCaseLockOfficerSummaryDto? = null,
    val cancellation_reason: String? = null,
    val refund_upi_id: String? = null,
    val refund_amount: Double? = null,
    val refund_transaction_id: String? = null,
    val refund_completed_at: String? = null,
    val media: List<AdminMediaDto>
)

data class AdminInstagramUrlUpdateRequestDto(@field:JsonAdapter(ExplicitNullJsonElementAdapter::class) val instagram_url: JsonElement)

private class ExplicitNullJsonElementAdapter : TypeAdapter<JsonElement>() {
    private val delegate = Gson().getAdapter(JsonElement::class.java)

    override fun write(out: JsonWriter, value: JsonElement?) {
        val previousSerializeNulls = out.serializeNulls
        out.serializeNulls = true
        try {
            delegate.write(out, value)
        } finally {
            out.serializeNulls = previousSerializeNulls
        }
    }

    override fun read(input: JsonReader): JsonElement? = delegate.read(input)
}

data class AdminInstagramUrlUpdateResponseDto(
    val request_id: Int,
    val instagram_url: String?
)

data class AdminMediaDto(
    val id: Int,
    val media_type: String,
    val document_type: String?,
    val file_url: String
)

data class ReviewActionRequestDto(
    val decision: String,
    val rejection_reason: String? = null
)

data class ReviewActionResponseDto(
    val status: String,
    val request_id: Int,
    val listing_status: String
)

data class AdminWorkflowSummaryDto(
    val pending_admin_review: Int,
    val assigned_to_field_officer: Int,
    val field_verified_final_approval: Int,
    val live_listings: Int,
    val locked_listings: Int,
    val booked_listings: Int,
    val sold_listings: Int,
    val rejected_listings: Int,
    val cancel_refund_management: Int,
    val pending_registry_verification: Int,
    val viewer: DashboardViewerDto?
)

data class AdminFieldOfficerOptionDto(
    val id: Int,
    val fullname: String,
    val mobile: String?,
    val is_active: Boolean
)

data class AdminCaseLockOfficerSummaryDto(
    val id: Int,
    val fullname: String,
    val mobile: String?
)

data class AdminCaseAssignmentBoardItemDto(
    val id: Int,
    val listing_code: String?,
    val owner_name: String?,
    val owner_mobile: String?,
    val location: String?,
    val assigned_field_officer: AdminCaseLockOfficerSummaryDto?,
    val lock_started_at: String?,
    val lock_expires_at: String?,
    val locked_for_seconds: Int?
)

data class AdminAssignmentBoardResponseDto(
    val locked_total: Int,
    val available_total: Int,
    val locked_cases: List<AdminCaseAssignmentBoardItemDto>,
    val available_cases: List<AdminCaseAssignmentBoardItemDto>
)

data class AdminAssignCaseRequestDto(
    val field_officer_id: Int,
    val lock_hours: Int = 12
)

data class AdminAssignCaseResponseDto(
    val status: String,
    val request_id: Int,
    val assigned_field_officer: AdminCaseLockOfficerSummaryDto,
    val lock_started_at: String,
    val lock_expires_at: String
)

data class AdminForceReleaseResponseDto(
    val status: String,
    val request_id: Int
)

data class AdminLockedListingBuyerDto(
    val id: Int,
    val fullname: String,
    val mobile: String?
)

data class AdminLockedListingItemDto(
    val id: Int,
    val listing_code: String?,
    val owner_name: String?,
    val owner_mobile: String?,
    val expected_price: Double?,
    val lock_started_at: String?,
    val lock_expires_at: String?,
    val locked_for_seconds: Int?,
    val seller: AdminRefundQueueSellerDto,
    val buyer: AdminLockedListingBuyerDto?,
    val offer_id: Int?,
    val offer_status: String?,
    val deal_price: Double?
)

data class AdminLockedListingListResponseDto(
    val total: Int,
    val skip: Int,
    val limit: Int,
    val items: List<AdminLockedListingItemDto>
)

data class AdminBookedListingBuyerDto(
    val id: Int?,
    val fullname: String,
    val mobile: String?
)

data class AdminBookedListingItemDto(
    val id: Int,
    val listing_code: String?,
    val owner_name: String?,
    val owner_mobile: String?,
    val expected_price: Double?,
    val booked_at: String?,
    val deal_price: Double?,
    val booking_fee_amount: Double?,
    val payment_status: String?,
    val booking_status: String?,
    val field_officer: AdminCaseLockOfficerSummaryDto?,
    val seller: AdminRefundQueueSellerDto,
    val buyer: AdminBookedListingBuyerDto?,
    val booking_id: Int?
)

data class AdminBookedListingListResponseDto(
    val total: Int,
    val skip: Int,
    val limit: Int,
    val items: List<AdminBookedListingItemDto>
)

data class AdminBookingDocumentDto(
    val name: String,
    val file_url: String
)

data class AdminBookingPartyInfoDto(
    val name: String,
    val mobile: String?,
    val documents: List<AdminBookingDocumentDto>
)

data class AdminBookedLandInfoDto(
    val expected_price: Double?,
    val deal_price: Double?,
    val location: String?
)

data class AdminBookedPaymentInfoDto(
    val token_amount: Double?,
    val remaining_amount: Double?,
    val payment_status: String?
)

data class AdminBookedListingDetailDto(
    val booking_id: Int,
    val listing_id: Int,
    val status: String,
    val booked_at: String?,
    val booking_status: String,
    val buyer: AdminBookingPartyInfoDto,
    val seller: AdminBookingPartyInfoDto,
    val land: AdminBookedLandInfoDto,
    val payment: AdminBookedPaymentInfoDto,
    val field_officer: AdminCaseLockOfficerSummaryDto?,
    val registry: AdminRegistryInfoDto?,
    val cancellation_reason: String? = null,
    val refund_decision: String? = null,
    val refund_status: String? = null,
    val approved_refund_amount: Double? = null,
    val actual_refunded_amount: Double? = null,
    val refund_reference: String? = null,
    val cancelled_at: String? = null
)

data class PropertyBookingCancellationPreviewDto(
    val booking_id: Int, val listing_id: Int, val listing_code: String?, val property_name: String?,
    val buyer_name: String, val buyer_mobile: String, val booking_status: String, val listing_status: String,
    val captured_payment_amount: Double?, val captured_at: String?, val can_cancel: Boolean,
    val blocking_reason: String?
)

data class PropertyBookingCancellationRequestDto(
    val refund_decision: String, val refund_amount: Double, val cancellation_reason: String
)

data class PropertyBookingCancellationResponseDto(
    val booking_id: Int, val listing_id: Int, val refund_id: Int, val booking_status: String,
    val listing_status: String, val refund_decision: String, val refund_status: String,
    val original_captured_amount: Double, val approved_refund_amount: Double
)

data class AdminRegistryProofDto(
    val id: Int,
    val file_url: String,
    val file_name: String,
    val created_at: String
)

data class AdminRegistryInfoDto(
    val registry_date: String?,
    val registry_time: String?,
    val registry_location: String?,
    val proof_url: String?,
    val proofs: List<AdminRegistryProofDto> = emptyList(),
    val proof_notes: String?,
    val status: String?
)

data class AdminRegistryScheduleRequestDto(
    val registry_date: String,
    val registry_time: String,
    val registry_location: String
)

data class AdminRegistryScheduleResponseDto(
    val status: String,
    val booking_id: Int,
    val booking_status: String,
    val registry: AdminRegistryInfoDto
)

data class AdminRegistryVerificationRequestDto(
    val decision: String
)

data class AdminRegistryVerificationResponseDto(
    val status: String,
    val booking_id: Int,
    val booking_status: String
)

data class AdminRegistryPendingItemDto(
    val booking_id: Int,
    val listing_id: Int,
    val seller_name: String?,
    val seller_mobile: String?,
    val buyer_name: String,
    val buyer_mobile: String,
    val registry_date: String?,
    val registry_time: String?,
    val registry_location: String?,
    val proof_url: String?,
    val proofs: List<AdminRegistryProofDto> = emptyList()
)

data class AdminRegistryPendingListResponseDto(
    val total: Int,
    val skip: Int,
    val limit: Int,
    val items: List<AdminRegistryPendingItemDto>
)

data class AdminBookingFieldOfficerUpdateRequestDto(
    val field_officer_id: Int
)

data class AdminBookingFieldOfficerUpdateResponseDto(
    val status: String,
    val booking_id: Int,
    val field_officer: AdminCaseLockOfficerSummaryDto?
)

data class AdminForceReleaseOfferLockResponseDto(
    val status: String,
    val request_id: Int
)

data class AdminFieldVerifiedCaseListResponseDto(
    val total: Int,
    val skip: Int,
    val limit: Int,
    val items: List<AdminFieldVerifiedCaseItemDto>
)

data class AdminFieldVerifiedCaseItemDto(
    val id: Int,
    val listing_code: String?,
    val owner_name: String?,
    val owner_mobile: String?,
    val location: String?,
    val field_officer: AdminCaseLockOfficerSummaryDto?,
    val field_officer_notes: String?,
    val field_officer_reviewed_at: String?,
    val visit_photo_url: String?
)

data class AdminFinalApprovalActionRequestDto(
    val decision: String,
    val rejection_reason: String? = null
)

data class AdminFinalApprovalActionResponseDto(
    val status: String,
    val request_id: Int,
    val listing_status: String,
    val rejection_reason: String?
)

data class AdminRefundQueueSellerDto(
    val id: Int,
    val fullname: String,
    val mobile: String
)

data class AdminRefundQueueItemDto(
    val request_id: Int,
    val listing_code: String?,
    val seller_uid: Int,
    val seller: AdminRefundQueueSellerDto,
    val cancellation_reason: String,
    val cancelled_at: String,
    val refund_due_at: String?,
    val refund_upi_id: String?,
    val total_paid: Double
)

data class AdminRefundQueueResponseDto(
    val total: Int,
    val skip: Int,
    val limit: Int,
    val items: List<AdminRefundQueueItemDto>
)

data class AdminForwardRefundResponseDto(
    val status: String,
    val request_id: Int,
    val forwarded_to_accounting_at: String
)

data class AdminRefundSuccessItemDto(
    val request_id: Int,
    val listing_code: String?,
    val seller_uid: Int,
    val seller: AdminRefundQueueSellerDto,
    val cancellation_reason: String,
    val status_before_cancellation: String?,
    val status_before_cancellation_label: String?,
    val cancellation_stage: String?,
    val cancelled_at: String,
    val refund_completed_at: String,
    val refund_amount: Double?,
    val refund_transaction_id: String?,
    val status: String
)

data class AdminRefundSuccessListResponseDto(
    val total: Int,
    val skip: Int,
    val limit: Int,
    val items: List<AdminRefundSuccessItemDto>
)
