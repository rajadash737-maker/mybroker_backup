package com.example.mybroker_admin.feature.accounting.refunds.model

enum class RefundStatus {
    PENDING,
    SUCCESS
}

data class RefundItem(
    val id: Int,
    val listingId: String,
    val sellerName: String,
    val sellerMobile: String,

    val isAdminInvolved: Boolean,
    val adminName: String?,
    val adminMobile: String?,
    val adminStatus: String?,

    val totalPaid: Int,
    val cancelDate: String,
    val sellerUpiId: String? = null,

    val refundAmount: Int? = null,
    val transactionId: String? = null,
    val refundedDate: String? = null,
    val cancelReason: String = "",

    val status: RefundStatus = RefundStatus.PENDING
)
