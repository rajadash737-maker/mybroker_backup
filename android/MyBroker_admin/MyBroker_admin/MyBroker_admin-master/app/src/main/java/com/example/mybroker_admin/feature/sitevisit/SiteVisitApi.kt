package com.example.mybroker_admin.feature.sitevisit

import com.google.gson.annotations.SerializedName
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.POST
import retrofit2.http.Query
import com.example.mybroker_admin.data.remote.dto.BoundaryPointDto

data class SiteVisitOfficerDto(val id: Int, val fullname: String?)
data class SiteVisitHistoryPersonDto(val id: Int, val fullname: String?)
data class SiteVisitListItemDto(
    val id: Int,
    @SerializedName("listing_id") val listingId: Int,
    @SerializedName("listing_code") val listingCode: String?,
    @SerializedName("property_name") val propertyName: String,
    @SerializedName("buyer_name") val buyerName: String,
    @SerializedName("buyer_mobile") val buyerMobile: String,
    @SerializedName("preferred_visit_date") val visitDate: String,
    @SerializedName("preferred_visit_time") val visitTime: String,
    @SerializedName("visitor_count") val visitorCount: Int,
    val status: String,
    @SerializedName("payment_status") val paymentStatus: String,
    @SerializedName("site_visit_fee_rupees") val fee: String,
    @SerializedName("paid_at") val paidAt: String?,
    @SerializedName("assigned_field_officer") val officer: SiteVisitOfficerDto?
)
data class SiteVisitListDto(val total: Int, val skip: Int, val limit: Int, val items: List<SiteVisitListItemDto>)
data class SiteVisitSummaryDto(
    @SerializedName("total_paid") val totalPaid: Int,
    val pending: Int,
    val assigned: Int,
    val scheduled: Int,
    @SerializedName("in_progress") val inProgress: Int,
    val completed: Int,
    val cancelled: Int,
    @SerializedName("refund_pending") val refundPending: Int,
    val refunded: Int,
    @SerializedName("refund_failed") val refundFailed: Int
)
data class SiteVisitPropertyDto(val city: String?, val state: String?, val location: String?, val title: String?)
data class SiteVisitHistoryDto(
    val id: Int = 0,
    val action: String,
    @SerializedName("actor_type") val actorType: String,
    val actor: SiteVisitHistoryPersonDto? = null,
    @SerializedName("previous_field_officer") val previousOfficer: SiteVisitHistoryPersonDto? = null,
    @SerializedName("field_officer") val fieldOfficer: SiteVisitHistoryPersonDto? = null,
    val note: String?,
    @SerializedName("created_at") val createdAt: String
)
data class SiteVisitWorkflowHistoryDto(
    @SerializedName("event_type") val eventType: String,
    @SerializedName("actor_id") val actorId: Int,
    @SerializedName("actor_role") val actorRole: String,
    val reason: String?,
    @SerializedName("previous_values") val previousValues: Map<String, Any?>?,
    @SerializedName("updated_values") val updatedValues: Map<String, Any?>?,
    @SerializedName("created_at") val createdAt: String
)
data class SiteVisitAdminActionRequestDto(val reason: String)
data class SiteVisitAdminActionResultDto(
    @SerializedName("booking_id") val bookingId: Int,
    @SerializedName("booking_status") val bookingStatus: String,
    val reason: String,
    @SerializedName("actor_id") val actorId: Int,
    @SerializedName("actor_role") val actorRole: String,
    @SerializedName("occurred_at") val occurredAt: String
)
data class SiteVisitAccountingSummaryDto(
    @SerializedName("total_site_visit_bookings") val totalBookings: Int,
    @SerializedName("paid_site_visits") val paid: Int,
    @SerializedName("pending_payments") val pendingPayments: Int,
    @SerializedName("cancelled_bookings") val cancelled: Int,
    @SerializedName("refund_requests") val refundRequests: Int,
    @SerializedName("refund_pending") val refundPending: Int,
    val refunded: Int,
    @SerializedName("refund_failed") val refundFailed: Int,
    @SerializedName("site_visit_revenue_paise") val revenuePaise: Long,
    @SerializedName("refund_amount_paise") val refundAmountPaise: Long
)
data class SiteVisitAccountingRefundDto(
    @SerializedName("refund_id") val refundId: Int,
    @SerializedName("booking_id") val bookingId: Int,
    @SerializedName("listing_id") val listingId: Int,
    @SerializedName("listing_code") val listingCode: String?,
    @SerializedName("property_name") val propertyName: String,
    @SerializedName("buyer_name") val buyerName: String,
    @SerializedName("buyer_mobile") val buyerMobile: String,
    @SerializedName("preferred_visit_date") val visitDate: String,
    @SerializedName("preferred_visit_time") val visitTime: String,
    @SerializedName("fee_paise") val feePaise: Int,
    @SerializedName("payment_status") val paymentStatus: String,
    @SerializedName("original_payment_reference") val paymentReference: String?,
    @SerializedName("cancellation_reason") val cancellationReason: String?,
    @SerializedName("eligible_amount_paise") val eligiblePaise: Int,
    @SerializedName("actual_refunded_amount_paise") val actualPaise: Int?,
    @SerializedName("buyer_upi_id") val buyerUpiId: String?,
    @SerializedName("transaction_reference") val transactionReference: String?,
    val status: String,
    @SerializedName("refunded_at") val refundedAt: String?,
    @SerializedName("accounting_user_id") val accountingUserId: Int?,
    @SerializedName("internal_note") val internalNote: String?,
    @SerializedName("failure_reason") val failureReason: String?,
    @SerializedName("created_at") val createdAt: String,
    val history: List<SiteVisitRefundHistoryDto> = emptyList()
)
data class SiteVisitAccountingRefundListDto(val total: Int, val skip: Int, val limit: Int, val items: List<SiteVisitAccountingRefundDto>)
data class SiteVisitRefundConfirmDto(
    @SerializedName("actual_refunded_amount_paise") val amountPaise: Int,
    @SerializedName("transaction_reference") val transactionReference: String,
    @SerializedName("internal_note") val internalNote: String?
)
data class SiteVisitRefundFailureDto(val reason: String)
data class SiteVisitRefundActionDto(val status: String, val idempotent: Boolean)
data class SiteVisitRefundHistoryDto(
    @SerializedName("actor_id") val actorId: Int,
    @SerializedName("actor_role") val actorRole: String,
    val action: String,
    @SerializedName("previous_status") val previousStatus: String?,
    @SerializedName("new_status") val newStatus: String,
    @SerializedName("actual_amount_paise") val actualAmountPaise: Int?,
    @SerializedName("transaction_reference") val transactionReference: String?,
    val note: String?,
    @SerializedName("created_at") val createdAt: String
)
data class SiteVisitAuditSummaryDto(
    @SerializedName("total_bookings") val totalBookings: Int,
    @SerializedName("paid_bookings") val paidBookings: Int,
    @SerializedName("unpaid_bookings") val unpaidBookings: Int,
    @SerializedName("pending_admin_review") val pendingAdminReview: Int,
    val assigned: Int,
    @SerializedName("in_progress") val inProgress: Int,
    val completed: Int,
    val cancelled: Int,
    @SerializedName("correction_requests") val correctionRequests: Int,
    @SerializedName("refund_pending") val refundPending: Int,
    @SerializedName("refunded_amount_paise") val refundedAmountPaise: Long,
    @SerializedName("failed_refunds") val failedRefunds: Int,
    @SerializedName("notification_events") val notificationEvents: Int
)
data class SiteVisitAuditItemDto(
    val id: Int,
    @SerializedName("listing_id") val listingId: Int,
    @SerializedName("listing_code") val listingCode: String?,
    @SerializedName("property_name") val propertyName: String,
    @SerializedName("buyer_name") val buyerName: String,
    @SerializedName("buyer_mobile") val buyerMobile: String,
    @SerializedName("preferred_visit_date") val visitDate: String,
    @SerializedName("preferred_visit_time") val visitTime: String,
    @SerializedName("visitor_count") val visitorCount: Int,
    val status: String,
    @SerializedName("payment_status") val paymentStatus: String,
    @SerializedName("site_visit_fee_rupees") val fee: String,
    @SerializedName("seller_name") val sellerName: String,
    @SerializedName("payment_order_id") val paymentOrderId: String?,
    @SerializedName("payment_id") val paymentId: String?,
    @SerializedName("paid_at") val paidAt: String?,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("assigned_field_officer") val officer: SiteVisitOfficerDto?
)
data class SiteVisitAuditListDto(val total: Int, val skip: Int, val limit: Int, val items: List<SiteVisitAuditItemDto>)
data class SiteVisitAuditDetailDto(
    val id: Int,
    @SerializedName("listing_id") val listingId: Int,
    @SerializedName("listing_code") val listingCode: String?,
    @SerializedName("property_name") val propertyName: String,
    @SerializedName("buyer_name") val buyerName: String,
    @SerializedName("buyer_mobile") val buyerMobile: String,
    @SerializedName("preferred_visit_date") val visitDate: String,
    @SerializedName("preferred_visit_time") val visitTime: String,
    @SerializedName("visitor_count") val visitorCount: Int,
    val status: String,
    @SerializedName("payment_status") val paymentStatus: String,
    @SerializedName("site_visit_fee_rupees") val fee: String,
    @SerializedName("assigned_field_officer") val officer: SiteVisitOfficerDto?,
    @SerializedName("seller_name") val sellerName: String,
    @SerializedName("payment_order_id") val paymentOrderId: String?,
    @SerializedName("payment_id") val paymentId: String?,
    @SerializedName("paid_at") val paidAt: String?,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("pickup_address") val pickupAddress: String,
    val message: String?,
    @SerializedName("started_at") val startedAt: String?,
    @SerializedName("completed_at") val completedAt: String?,
    @SerializedName("cancelled_at") val cancelledAt: String?,
    @SerializedName("cancellation_actor_role") val cancellationActorRole: String?,
    @SerializedName("payment_history") val paymentHistory: List<Map<String, Any?>>,
    @SerializedName("assignment_history") val assignmentHistory: List<Map<String, Any?>>,
    @SerializedName("workflow_history") val workflowHistory: List<Map<String, Any?>>,
    @SerializedName("refund_history") val refundHistory: List<Map<String, Any?>>,
    @SerializedName("notification_history") val notificationHistory: List<Map<String, Any?>>,
    @SerializedName("cancellation_reason") val cancellationReason: String?
)
data class SiteVisitDetailDto(
    val id: Int,
    @SerializedName("listing_id") val listingId: Int,
    @SerializedName("listing_code") val listingCode: String?,
    @SerializedName("property_name") val propertyName: String,
    @SerializedName("buyer_name") val buyerName: String,
    @SerializedName("buyer_mobile") val buyerMobile: String,
    @SerializedName("preferred_visit_date") val visitDate: String,
    @SerializedName("preferred_visit_time") val visitTime: String,
    @SerializedName("visitor_count") val visitorCount: Int,
    val status: String,
    @SerializedName("payment_status") val paymentStatus: String,
    @SerializedName("site_visit_fee_rupees") val fee: String,
    @SerializedName("assigned_field_officer") val officer: SiteVisitOfficerDto?,
    @SerializedName("seller_name") val sellerName: String? = null,
    @SerializedName("seller_mobile") val sellerMobile: String? = null,
    @SerializedName("pickup_address") val pickupAddress: String,
    val message: String?,
    @SerializedName("assignment_history") val history: List<SiteVisitHistoryDto> = emptyList(),
    val property: SiteVisitPropertyDto? = null,
    @SerializedName("scheduled_at") val scheduledAt: String? = null,
    @SerializedName("started_at") val startedAt: String? = null,
    @SerializedName("completed_at") val completedAt: String? = null,
    @SerializedName("cancelled_at") val cancelledAt: String? = null,
    @SerializedName("cancellation_reason") val cancellationReason: String? = null,
    @SerializedName("cancelled_by_id") val cancelledById: Int? = null,
    @SerializedName("cancellation_actor_role") val cancellationActorRole: String? = null,
    @SerializedName("correction_reason") val correctionReason: String? = null,
    @SerializedName("workflow_history") val workflowHistory: List<SiteVisitWorkflowHistoryDto> = emptyList()
)
data class SiteVisitAssignmentRequestDto(@SerializedName("field_officer_id") val officerId: Int, val note: String? = null)
data class SiteVisitUnassignmentRequestDto(val note: String? = null)
data class SiteVisitAssignmentResultDto(val status: String, val action: String)
data class FieldOfficerVisitDto(
    val id: Int,
    @SerializedName("listing_id") val listingId: Int,
    @SerializedName("listing_code") val listingCode: String?,
    @SerializedName("land_boundary_points") val landBoundaryPoints: List<BoundaryPointDto> = emptyList(),
    @SerializedName("property_name") val propertyName: String,
    @SerializedName("buyer_name") val buyerName: String,
    @SerializedName("buyer_mobile") val buyerMobile: String,
    @SerializedName("preferred_visit_date") val visitDate: String,
    @SerializedName("preferred_visit_time") val visitTime: String,
    @SerializedName("visitor_count") val visitorCount: Int,
    @SerializedName("pickup_address") val pickupAddress: String,
    val message: String?,
    val status: String,
    @SerializedName("payment_status") val paymentStatus: String,
    @SerializedName("site_visit_fee_rupees") val fee: String,
    @SerializedName("started_at") val startedAt: String?,
    @SerializedName("completed_at") val completedAt: String?,
    @SerializedName("assigned_at") val assignedAt: String? = null,
    @SerializedName("assignment_note") val assignmentNote: String? = null
)
data class FieldVisitActionDto(@SerializedName("booking_id") val bookingId: Int, @SerializedName("booking_status") val status: String)
data class CompletionCodeRequestDto(@SerializedName("completion_code") val code: String)

interface SiteVisitApi {
    @GET("site-visits/admin") suspend fun list(@Query("skip") skip: Int = 0, @Query("limit") limit: Int = 100, @Query("status") status: String? = null): SiteVisitListDto
    @GET("site-visits/admin/summary") suspend fun summary(): SiteVisitSummaryDto
    @GET("site-visits/super-admin/audit/summary") suspend fun auditSummary(): SiteVisitAuditSummaryDto
    @GET("site-visits/super-admin/audit/bookings") suspend fun auditBookings(
        @Query("skip") skip: Int = 0, @Query("limit") limit: Int = 25,
        @Query("booking_id") bookingId: Int? = null, @Query("listing_id") listingId: Int? = null,
        @Query("listing_code") listingCode: String? = null, @Query("buyer_search") buyer: String? = null,
        @Query("officer_search") officerSearch: String? = null,
        @Query("officer_id") officerId: Int? = null, @Query("admin_id") adminId: Int? = null,
        @Query("accounting_id") accountingId: Int? = null, @Query("reference_search") reference: String? = null,
        @Query("date_from") dateFrom: String? = null, @Query("date_to") dateTo: String? = null
    ): SiteVisitAuditListDto
    @GET("site-visits/super-admin/audit/bookings/{id}") suspend fun auditDetail(@Path("id") id: Int): SiteVisitAuditDetailDto
    @GET("site-visits/admin/field-officers") suspend fun officers(): List<SiteVisitOfficerDto>
    @GET("site-visits/admin/{id}") suspend fun detail(@Path("id") id: Int): SiteVisitDetailDto
    @POST("site-visits/admin/{id}/correction") suspend fun requestCorrection(@Path("id") id: Int, @Body request: SiteVisitAdminActionRequestDto): SiteVisitAdminActionResultDto
    @POST("site-visits/admin/{id}/cancel") suspend fun cancel(@Path("id") id: Int, @Body request: SiteVisitAdminActionRequestDto): SiteVisitAdminActionResultDto
    @GET("site-visits/accounting/summary") suspend fun accountingSummary(): SiteVisitAccountingSummaryDto
    @GET("site-visits/accounting/refunds") suspend fun accountingRefunds(@Query("skip") skip: Int = 0, @Query("limit") limit: Int = 100, @Query("status") status: String? = null, @Query("search") search: String? = null): SiteVisitAccountingRefundListDto
    @POST("site-visits/accounting/refunds/{id}/confirm") suspend fun confirmRefund(@Path("id") id: Int, @Body request: SiteVisitRefundConfirmDto): SiteVisitRefundActionDto
    @POST("site-visits/accounting/refunds/{id}/fail") suspend fun failRefund(@Path("id") id: Int, @Body request: SiteVisitRefundFailureDto): SiteVisitRefundActionDto
    @PUT("site-visits/admin/{id}/assignment") suspend fun assign(@Path("id") id: Int, @Body request: SiteVisitAssignmentRequestDto): SiteVisitAssignmentResultDto
    @DELETE("site-visits/admin/{id}/assignment") suspend fun unassign(@Path("id") id: Int, @Body request: SiteVisitUnassignmentRequestDto): Response<ResponseBody>
    @GET("site-visits/field-officer/my-visits") suspend fun myVisits(): List<FieldOfficerVisitDto>
    @POST("site-visits/field-officer/{id}/start") suspend fun start(@Path("id") id: Int): FieldVisitActionDto
    @POST("site-visits/field-officer/{id}/completion-code") suspend fun initiateCompletion(@Path("id") id: Int): FieldVisitActionDto
    @POST("site-visits/field-officer/{id}/verify-completion") suspend fun verifyCompletion(@Path("id") id: Int, @Body request: CompletionCodeRequestDto): FieldVisitActionDto
}


