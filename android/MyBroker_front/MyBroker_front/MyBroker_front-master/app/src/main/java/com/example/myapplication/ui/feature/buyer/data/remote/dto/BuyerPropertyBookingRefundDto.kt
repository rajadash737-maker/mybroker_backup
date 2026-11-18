package com.example.myapplication.ui.feature.buyer.data.remote.dto

import com.google.gson.annotations.SerializedName

data class BuyerPropertyBookingRefundDto(
    @SerializedName("booking_id") val bookingId: Int,
    @SerializedName("listing_id") val listingId: Int,
    @SerializedName("booking_status") val bookingStatus: String,
    @SerializedName("refund_decision") val refundDecision: String,
    @SerializedName("refund_status") val refundStatus: String,
    @SerializedName("cancellation_reason") val cancellationReason: String,
    @SerializedName("approved_refund_amount") val approvedRefundAmount: Double,
    @SerializedName("actual_refunded_amount") val actualRefundedAmount: Double?,
    @SerializedName("transaction_reference") val transactionReference: String?,
    @SerializedName("accounting_confirmed_at") val accountingConfirmedAt: String?
)

data class BuyerRefundUpiRequestDto(@SerializedName("upi_id") val upiId: String)
