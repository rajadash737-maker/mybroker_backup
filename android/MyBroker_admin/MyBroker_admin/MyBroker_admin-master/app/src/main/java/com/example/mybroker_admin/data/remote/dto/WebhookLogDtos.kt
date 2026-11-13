package com.example.mybroker_admin.data.remote.dto

import com.google.gson.annotations.SerializedName

data class WebhookLogItemDto(
    @SerializedName("id") val id: Int,
    @SerializedName("event_id") val eventId: String? = null,
    @SerializedName("event") val event: String,
    @SerializedName("order_id") val orderId: String? = null,
    @SerializedName("payment_id") val paymentId: String? = null,
    @SerializedName("status") val status: String,
    @SerializedName("payment_context") val paymentContext: String,
    @SerializedName("error") val error: String? = null,
    @SerializedName("payload") val payload: String,
    @SerializedName("created_at") val createdAt: String
)

data class WebhookLogListResponseDto(
    @SerializedName("total") val total: Int,
    @SerializedName("items") val items: List<WebhookLogItemDto>
)
