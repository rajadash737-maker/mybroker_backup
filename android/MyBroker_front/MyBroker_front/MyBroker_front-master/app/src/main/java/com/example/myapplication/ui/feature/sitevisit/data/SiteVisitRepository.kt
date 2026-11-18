package com.example.myapplication.ui.feature.sitevisit.data

import com.example.myapplication.network.ApiClient

class SiteVisitRepository {
    private val api by lazy { ApiClient.createService(SiteVisitApi::class.java) }
    suspend fun fee() = api.fee()
    suspend fun create(request: SiteVisitCreateRequest) = api.create(request)
    suspend fun bookings() = api.myBookings()
    suspend fun order(bookingId: Int) = api.createOrder(bookingId)
    suspend fun verify(bookingId: Int, request: SiteVisitVerifyPaymentRequest) = api.verify(bookingId, request)
    suspend fun cancelPayment(bookingId: Int) = api.cancelPayment(bookingId)
    suspend fun cancel(bookingId: Int, request: SiteVisitCancelRequest) = api.cancel(bookingId, request)
    suspend fun resubmitCorrection(bookingId: Int, request: SiteVisitCorrectionResponseRequest) = api.resubmitCorrection(bookingId, request)
    suspend fun submitRefundDetails(bookingId: Int, request: SiteVisitRefundDetailsRequest) = api.submitRefundDetails(bookingId, request)
}
