package com.example.myapplication.ui.feature.transactions.data.remote

import com.google.gson.annotations.SerializedName

data class TransactionDto(
    @SerializedName("transaction_id") val transactionId: String? = null,
    @SerializedName("property_title") val propertyTitle: String = "",
    @SerializedName("buyer_name") val buyerName: String = "",
    @SerializedName("seller_name") val sellerName: String = "",
    val location: String = "",
    @SerializedName("deal_amount") val dealAmount: Long = 0L,
    @SerializedName("payment_status") val paymentStatus: String = "",
    @SerializedName("deal_status") val dealStatus: String = "",
    @SerializedName("offer_status") val offerStatus: String? = null,
    @SerializedName("offer_status_at") val offerStatusAt: String? = null,
    @SerializedName("registry_date") val registryDate: String? = null,
    @SerializedName("created_at") val createdAt: String? = null
) {
    val id: String get() = transactionId.orEmpty()
}

data class TransactionsResponse(val data: List<TransactionDto> = emptyList())
