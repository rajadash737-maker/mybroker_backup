package com.example.mybroker_admin.data.remote.dto

data class PropertyBookingRefundQueueDto(val total: Int, val skip: Int, val limit: Int, val items: List<PropertyBookingRefundItemDto>)
data class PropertyBookingRefundItemDto(
    val refund_id: Int, val booking_id: Int, val listing_id: Int, val listing_code: String?, val property_name: String?,
    val buyer_name: String, val buyer_mobile: String, val original_captured_amount: Double,
    val approved_refund_amount: Double, val cancellation_reason: String, val refund_status: String, val cancelled_at: String,
    val buyer_upi_id: String? = null
)
data class PropertyBookingRefundHistoryDto(
    val event_type: String, val from_status: String?, val to_status: String, val actor_role: String,
    val note: String?, val created_at: String
)
data class PropertyBookingRefundDetailDto(
    val refund_id: Int, val booking_id: Int, val listing_id: Int, val listing_code: String?, val property_name: String?,
    val buyer_name: String, val buyer_mobile: String, val original_captured_amount: Double,
    val approved_refund_amount: Double, val cancellation_reason: String, val refund_status: String, val cancelled_at: String,
    val buyer_id: Int, val buyer_upi_id: String?, val transaction_reference: String?, val actual_refunded_amount: Double?,
    val confirmation_note: String?, val accounting_confirmed_at: String?, val payment_order_id: Int,
    val history: List<PropertyBookingRefundHistoryDto>
)
data class PropertyBookingRefundConfirmRequestDto(
    val actual_refunded_amount: Double, val transaction_reference: String, val confirmation_note: String? = null
)
data class PropertyBookingRefundFailRequestDto(val reason: String)

data class AccountingRefundPendingItemDto(
    val request_id: Int,
    val listing_code: String?,
    val seller_uid: Int,
    val seller_fullname: String,
    val seller_mobile: String,
    val cancellation_reason: String,
    val cancelled_at: String,
    val refund_due_at: String?,
    val refund_upi_id: String?,
    val total_paid: Double,
    val admin_involved: Boolean,
    val admin_name: String?,
    val admin_mobile: String?,
    val admin_status: String?
)

data class AccountingRefundPendingResponseDto(
    val total: Int,
    val skip: Int,
    val limit: Int,
    val items: List<AccountingRefundPendingItemDto>
)

data class AccountingRefundHistoryItemDto(
    val request_id: Int,
    val listing_code: String?,
    val seller_uid: Int,
    val seller_fullname: String,
    val seller_mobile: String,
    val cancellation_reason: String,
    val cancelled_at: String,
    val refund_upi_id: String?,
    val refund_completed_at: String,
    val total_paid: Double,
    val admin_involved: Boolean,
    val admin_name: String?,
    val admin_mobile: String?,
    val admin_status: String?,
    val refund_amount: Double?,
    val refund_transaction_id: String?,
    val status: String
)

data class AccountingRefundHistoryResponseDto(
    val total: Int,
    val skip: Int,
    val limit: Int,
    val items: List<AccountingRefundHistoryItemDto>
)

data class AccountingConfirmRefundRequestDto(
    val refund_amount: Double? = null,
    val transaction_id: String? = null
)

data class AccountingConfirmRefundResponseDto(
    val status: String,
    val request_id: Int,
    val listing_status: String,
    val refund_completed_at: String,
    val refund_amount: Double?,
    val refund_transaction_id: String?
)

data class AccountingDashboardSummaryDto(
    val total_revenue: Double,
    val pending_payments: Int,
    val completed_transactions: Int,
    val pending_refunds: Int
)

data class SuperAdminRevenueRangeDto(
    val type: String,
    val start: String,
    val end: String
)

data class SuperAdminRevenueBreakdownDto(
    val total: Double,
    val seller: Double,
    val buyer: Double
)

data class SuperAdminRevenueTransactionDto(
    val date: String,
    val type: String,
    val user_name: String,
    val amount: Double,
    val status: String
)

data class SuperAdminRevenueDashboardDto(
    val range: SuperAdminRevenueRangeDto,
    val revenue: SuperAdminRevenueBreakdownDto,
    val transactions: List<SuperAdminRevenueTransactionDto>
)

data class AccountingCompletedTransactionItemDto(
    val listing_id: Int,
    val listing_code: String?,
    val seller_name: String,
    val seller_fee: Double,
    val seller_fee_status: String,
    val buyer_name: String?,
    val buyer_fee: Double?,
    val buyer_fee_status: String,
    val status: String,
    val date: String
)

data class AccountingCompletedTransactionListResponseDto(
    val total: Int,
    val skip: Int,
    val limit: Int,
    val items: List<AccountingCompletedTransactionItemDto>
)



data class AccountingPaymentInfoDto(
    val method: String?,
    val transaction_id: String?,
    val paid_at: String?,
    val status: String?
)

data class AccountingPaymentDetailsDto(
    val seller: AccountingPaymentInfoDto?,
    val buyer: AccountingPaymentInfoDto?
)

data class AccountingCompletedTransactionDetailResponseDto(
    val transaction: AccountingCompletedTransactionItemDto,
    val payment_details: AccountingPaymentDetailsDto?,
    val land_price_note: String,
    val final_status: String
)
