package com.example.myapplication.ui.feature.sitevisit.data

import com.google.gson.annotations.SerializedName
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

data class SiteVisitCreateRequest(
    @SerializedName("listing_id") val listingId: Int,
    @SerializedName("preferred_visit_date") val preferredVisitDate: String,
    @SerializedName("preferred_visit_time") val preferredVisitTime: String,
    @SerializedName("visitor_count") val visitorCount: Int,
    @SerializedName("pickup_address") val pickupAddress: String,
    val message: String?,
    @SerializedName("submission_key") val submissionKey: String
)
data class SiteVisitFeeDto(@SerializedName("site_visit_fee_rupees") val rupees: String, @SerializedName("site_visit_fee_paise") val paise: Int, val currency: String)
data class SiteVisitBookingDto(
    val id: Int, @SerializedName("listing_id") val listingId: Int, @SerializedName("listing_code") val listingCode: String?,
    @SerializedName("property_name") val propertyName: String, @SerializedName("buyer_name") val buyerName: String,
    @SerializedName("buyer_mobile") val buyerMobile: String, @SerializedName("preferred_visit_date") val visitDate: String,
    @SerializedName("preferred_visit_time") val visitTime: String, @SerializedName("visitor_count") val visitorCount: Int,
    @SerializedName("pickup_address") val pickupAddress: String, val message: String?,
    @SerializedName("booking_status") val bookingStatus: String, @SerializedName("payment_status") val paymentStatus: String,
    @SerializedName("site_visit_fee_rupees") val feeRupees: String, @SerializedName("site_visit_fee_paise") val feePaise: Int,
    @SerializedName("completion_code") val completionCode: String? = null,
    @SerializedName("completion_code_expires_at") val completionCodeExpiresAt: String? = null,
    @SerializedName("cancellation_reason") val cancellationReason: String? = null,
    @SerializedName("cancelled_by_role") val cancelledByRole: String? = null,
    @SerializedName("correction_reason") val correctionReason: String? = null,
    @SerializedName("correction_requested_at") val correctionRequestedAt: String? = null,
    @SerializedName("workflow_history") val workflowHistory: List<SiteVisitWorkflowHistoryDto> = emptyList(),
    val refund: SiteVisitRefundDto? = null
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
data class SiteVisitCorrectionResponseRequest(
    @SerializedName("preferred_visit_date") val visitDate: String,
    @SerializedName("preferred_visit_time") val visitTime: String,
    @SerializedName("visitor_count") val visitorCount: Int,
    @SerializedName("pickup_address") val pickupAddress: String,
    val message: String?
)
data class SiteVisitRefundDetailsRequest(@SerializedName("upi_id") val upiId: String)
data class SiteVisitRefundDto(
    val eligible: Boolean,
    @SerializedName("eligible_amount_paise") val eligibleAmountPaise: Int,
    val status: String?,
    @SerializedName("actual_refunded_amount_paise") val actualRefundedAmountPaise: Int?,
    @SerializedName("transaction_reference") val transactionReference: String?,
    @SerializedName("refunded_at") val refundedAt: String?
)
data class SiteVisitOrderDto(@SerializedName("booking_id") val bookingId: Int, @SerializedName("order_id") val orderId: String, @SerializedName("amount_paise") val amountPaise: Int, val currency: String, @SerializedName("payment_status") val paymentStatus: String)
data class SiteVisitVerifyPaymentRequest(@SerializedName("razorpay_order_id") val orderId: String, @SerializedName("razorpay_payment_id") val paymentId: String, @SerializedName("razorpay_signature") val signature: String)
data class SiteVisitPaymentResultDto(val status: String, @SerializedName("order_id") val orderId: String, @SerializedName("payment_id") val paymentId: String)
data class SiteVisitPaymentAttemptDto(@SerializedName("booking_id") val bookingId: Int, @SerializedName("order_id") val orderId: String, @SerializedName("payment_status") val paymentStatus: String)
data class SiteVisitCancelRequest(val reason: String)
data class SiteVisitCancelResponse(
    val status: String,
    @SerializedName("booking_id") val bookingId: Int,
    @SerializedName("booking_status") val bookingStatus: String,
    @SerializedName("cancellation_reason") val cancellationReason: String,
    @SerializedName("cancelled_at") val cancelledAt: String
)

interface SiteVisitApi {
    @GET("site-visits/fee") suspend fun fee(): SiteVisitFeeDto
    @POST("site-visits") suspend fun create(@Body request: SiteVisitCreateRequest): SiteVisitBookingDto
    @GET("site-visits/my-bookings") suspend fun myBookings(): List<SiteVisitBookingDto>
    @POST("site-visits/{bookingId}/payment-order") suspend fun createOrder(@Path("bookingId") bookingId: Int): SiteVisitOrderDto
    @POST("site-visits/{bookingId}/verify-payment") suspend fun verify(@Path("bookingId") bookingId: Int, @Body request: SiteVisitVerifyPaymentRequest): SiteVisitPaymentResultDto
    @POST("site-visits/{bookingId}/cancel-payment") suspend fun cancelPayment(@Path("bookingId") bookingId: Int): SiteVisitPaymentAttemptDto
    @POST("site-visits/{bookingId}/cancel") suspend fun cancel(@Path("bookingId") bookingId: Int, @Body request: SiteVisitCancelRequest): SiteVisitCancelResponse
    @POST("site-visits/{bookingId}/correction-response") suspend fun resubmitCorrection(@Path("bookingId") bookingId: Int, @Body request: SiteVisitCorrectionResponseRequest): SiteVisitBookingDto
    @POST("site-visits/{bookingId}/refund-details") suspend fun submitRefundDetails(@Path("bookingId") bookingId: Int, @Body request: SiteVisitRefundDetailsRequest): Map<String, Any?>
}

