package com.example.mybroker_admin.data.repository

import com.example.mybroker_admin.data.remote.api.AccountingListingApi
import com.example.mybroker_admin.data.remote.dto.AccountingConfirmRefundRequestDto

class AccountingListingRepository(
    private val api: AccountingListingApi
) {

    suspend fun getPendingRefunds(skip: Int = 0, limit: Int = 20) =
        api.getPendingRefunds(skip = skip, limit = limit)

    suspend fun getRefundHistory(skip: Int = 0, limit: Int = 20) =
        api.getRefundHistory(skip = skip, limit = limit)

    suspend fun confirmRefund(requestId: Int, amount: Int, txnId: String) =
        api.confirmRefund(
            id = requestId,
            body = AccountingConfirmRefundRequestDto(
                refund_amount = amount.toDouble(),
                transaction_id = txnId
            )
        )

    suspend fun getCompletedTransactions(skip: Int = 0, limit: Int = 20) =
        api.getCompletedTransactions(skip = skip, limit = limit)

    suspend fun getCompletedTransactionDetail(listingId: Int) =
        api.getCompletedTransactionDetail(listingId)

    suspend fun getDashboardSummary(range: String, start: String? = null, end: String? = null) =
        api.getDashboardSummary(range = range, start = start, end = end)

    suspend fun getSuperAdminRevenueDashboard(range: String, start: String? = null, end: String? = null) =
        api.getSuperAdminRevenueDashboard(range = range, start = start, end = end)
}
