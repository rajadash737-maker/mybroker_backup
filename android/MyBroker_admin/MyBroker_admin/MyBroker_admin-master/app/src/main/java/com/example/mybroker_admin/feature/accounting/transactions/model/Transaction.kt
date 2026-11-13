package com.example.mybroker_admin.feature.accounting.transactions.model

data class Transaction(
    val listingId: String,
    val sellerName: String,
    val sellerFee: Double,
    val sellerFeeStatus: String,
    val buyerName: String?,
    val buyerFee: Double?,
    val buyerFeeStatus: String,
    val status: String,
    val date: String
)



data class PaymentInfo(
    val method: String?,
    val transactionId: String?,
    val paidAt: String?,
    val status: String?
)

data class PaymentDetails(
    val seller: PaymentInfo?,
    val buyer: PaymentInfo?
)

data class TransactionDetail(
    val transaction: Transaction,
    val landPriceNote: String,
    val finalStatus: String,
    val paymentDetails: PaymentDetails
)
