package com.example.myapplication.ui.feature.buyer.data.remote.dto

import com.google.gson.annotations.SerializedName

data class BookingPaymentRequestDto(
    @SerializedName("method") val method: String,
    @SerializedName("transaction_id") val transactionId: String? = null
)

data class CreateOrderRequestDto(
    @SerializedName("amount") val amount: Double,
    @SerializedName("user_id") val user_id: Int,
    @SerializedName("property_id") val property_id: Int
)

data class CreateOrderResponseDto(
    @SerializedName("order_id") val order_id: String,
    @SerializedName("amount") val amount: Int,
    @SerializedName("currency") val currency: String
)

data class VerifyPaymentRequestDto(
    @SerializedName("razorpay_order_id") val razorpay_order_id: String,
    @SerializedName("razorpay_payment_id") val razorpay_payment_id: String,
    @SerializedName("razorpay_signature") val razorpay_signature: String
)

data class VerifyPaymentResponseDto(
    @SerializedName("status") val status: String,
    @SerializedName("order_id") val order_id: String,
    @SerializedName("payment_id") val payment_id: String
)
