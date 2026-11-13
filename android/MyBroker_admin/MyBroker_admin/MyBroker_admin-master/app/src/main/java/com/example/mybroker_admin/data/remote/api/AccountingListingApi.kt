package com.example.mybroker_admin.data.remote.api

import com.example.mybroker_admin.data.remote.dto.AccountingConfirmRefundRequestDto
import com.example.mybroker_admin.data.remote.dto.AccountingConfirmRefundResponseDto
import com.example.mybroker_admin.data.remote.dto.AccountingCompletedTransactionDetailResponseDto
import com.example.mybroker_admin.data.remote.dto.AccountingCompletedTransactionListResponseDto
import com.example.mybroker_admin.data.remote.dto.AccountingDashboardSummaryDto
import com.example.mybroker_admin.data.remote.dto.SuperAdminRevenueDashboardDto
import com.example.mybroker_admin.data.remote.dto.AccountingRefundHistoryResponseDto
import com.example.mybroker_admin.data.remote.dto.AccountingRefundPendingResponseDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.PATCH
import retrofit2.http.Path
import retrofit2.http.Query

interface AccountingListingApi {

    @GET("admin/sell-land/accounting/refunds/pending")
    suspend fun getPendingRefunds(
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 20
    ): AccountingRefundPendingResponseDto

    @GET("admin/sell-land/accounting/refunds/history")
    suspend fun getRefundHistory(
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 20
    ): AccountingRefundHistoryResponseDto

    @PATCH("admin/sell-land/accounting/refunds/{id}/confirm")
    suspend fun confirmRefund(
        @Path("id") id: Int,
        @Body body: AccountingConfirmRefundRequestDto
    ): AccountingConfirmRefundResponseDto

    @GET("admin/sell-land/accounting/transactions/completed")
    suspend fun getCompletedTransactions(
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 20
    ): AccountingCompletedTransactionListResponseDto

    @GET("admin/sell-land/accounting/transactions/{listingId}")
    suspend fun getCompletedTransactionDetail(
        @Path("listingId") listingId: Int
    ): AccountingCompletedTransactionDetailResponseDto

    @GET("admin/sell-land/accounting/dashboard/summary")
    suspend fun getDashboardSummary(
        @Query("range") range: String,
        @Query("start") start: String? = null,
        @Query("end") end: String? = null
    ): AccountingDashboardSummaryDto

    @GET("admin/sell-land/super-admin/dashboard/revenue")
    suspend fun getSuperAdminRevenueDashboard(
        @Query("range") range: String,
        @Query("start") start: String? = null,
        @Query("end") end: String? = null
    ): SuperAdminRevenueDashboardDto
}
