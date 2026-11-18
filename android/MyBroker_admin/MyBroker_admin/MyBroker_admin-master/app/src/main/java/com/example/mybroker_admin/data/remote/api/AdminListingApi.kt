package com.example.mybroker_admin.data.remote.api

import com.example.mybroker_admin.data.remote.dto.AdminAssignCaseRequestDto
import com.example.mybroker_admin.data.remote.dto.AdminAssignCaseResponseDto
import com.example.mybroker_admin.data.remote.dto.AdminAssignmentBoardResponseDto
import com.example.mybroker_admin.data.remote.dto.AdminFieldOfficerOptionDto
import com.example.mybroker_admin.data.remote.dto.AdminFieldVerifiedCaseListResponseDto
import com.example.mybroker_admin.data.remote.dto.AdminFinalApprovalActionRequestDto
import com.example.mybroker_admin.data.remote.dto.AdminFinalApprovalActionResponseDto
import com.example.mybroker_admin.data.remote.dto.AdminForceReleaseResponseDto
import com.example.mybroker_admin.data.remote.dto.AdminForceReleaseOfferLockResponseDto
import com.example.mybroker_admin.data.remote.dto.AdminForwardRefundResponseDto
import com.example.mybroker_admin.data.remote.dto.AdminListingDetailDto
import com.example.mybroker_admin.data.remote.dto.AdminListingListResponseDto
import com.example.mybroker_admin.data.remote.dto.AdminInstagramUrlUpdateRequestDto
import com.example.mybroker_admin.data.remote.dto.AdminInstagramUrlUpdateResponseDto
import com.example.mybroker_admin.data.remote.dto.AdminBookedListingListResponseDto
import com.example.mybroker_admin.data.remote.dto.AdminBookedListingDetailDto
import com.example.mybroker_admin.data.remote.dto.AdminBookingFieldOfficerUpdateRequestDto
import com.example.mybroker_admin.data.remote.dto.AdminBookingFieldOfficerUpdateResponseDto
import com.example.mybroker_admin.data.remote.dto.AdminRegistryScheduleRequestDto
import com.example.mybroker_admin.data.remote.dto.AdminRegistryScheduleResponseDto
import com.example.mybroker_admin.data.remote.dto.AdminRegistryVerificationRequestDto
import com.example.mybroker_admin.data.remote.dto.AdminRegistryVerificationResponseDto
import com.example.mybroker_admin.data.remote.dto.AdminRegistryPendingListResponseDto
import com.example.mybroker_admin.data.remote.dto.AdminLockedListingListResponseDto
import com.example.mybroker_admin.data.remote.dto.AdminRefundQueueResponseDto
import com.example.mybroker_admin.data.remote.dto.AdminRefundSuccessListResponseDto
import com.example.mybroker_admin.data.remote.dto.AdminWorkflowSummaryDto
import com.example.mybroker_admin.data.remote.dto.AdminRatingListItemDto
import com.example.mybroker_admin.data.remote.dto.ReviewActionRequestDto
import com.example.mybroker_admin.data.remote.dto.ReviewActionResponseDto
import com.example.mybroker_admin.data.remote.dto.WebhookLogListResponseDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query
import retrofit2.Response
import com.example.mybroker_admin.data.remote.dto.PropertyBookingCancellationPreviewDto
import com.example.mybroker_admin.data.remote.dto.PropertyBookingCancellationRequestDto
import com.example.mybroker_admin.data.remote.dto.PropertyBookingCancellationResponseDto

interface AdminListingApi {
    @GET("admin/sell-land/bookings/{bookingId}/cancellation-preview")
    suspend fun getBookingCancellationPreview(@Path("bookingId") bookingId: Int): Response<PropertyBookingCancellationPreviewDto>

    @POST("admin/sell-land/bookings/{bookingId}/cancel")
    suspend fun cancelPropertyBooking(
        @Path("bookingId") bookingId: Int,
        @Body body: PropertyBookingCancellationRequestDto
    ): PropertyBookingCancellationResponseDto

    @GET("admin/sell-land/dashboard/workflow-summary")
    suspend fun getWorkflowSummary(): AdminWorkflowSummaryDto

    @GET("admin/sell-land/requests")
    suspend fun getRequests(
        @Query("status") status: String = "pending",
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 20,
        @Query("search") search: String? = null,
        @Query("state") state: String? = null,
        @Query("district") district: String? = null
    ): AdminListingListResponseDto

    @GET("admin/sell-land/requests/all")
    suspend fun getAllRequests(
        @Query("status") status: String? = null,
        @Query("listing_id") listingId: Int? = null,
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 20,
        @Query("search") search: String? = null,
        @Query("state") state: String? = null,
        @Query("district") district: String? = null
    ): AdminListingListResponseDto

    @GET("admin/sell-land/requests/{id}")
    suspend fun getRequestDetail(@Path("id") id: Int): AdminListingDetailDto

    @PATCH("admin/sell-land/requests/{id}/instagram")
    suspend fun updateListingInstagramUrl(
        @Path("id") id: Int,
        @Body body: AdminInstagramUrlUpdateRequestDto
    ): AdminInstagramUrlUpdateResponseDto

    @PATCH("admin/sell-land/requests/{id}/review")
    suspend fun reviewRequest(
        @Path("id") id: Int,
        @Body body: ReviewActionRequestDto
    ): ReviewActionResponseDto

    @GET("admin/sell-land/requests")
    suspend fun getPending(
        @Query("status") status: String = "pending",
        @Query("state") state: String? = null,
        @Query("district") district: String? = null,
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 20
    ): AdminListingListResponseDto

    @GET("admin/sell-land/requests")
    suspend fun getRequestsByStatus(
        @Query("status") status: String,
        @Query("state") state: String? = null,
        @Query("district") district: String? = null,
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 20
    ): AdminListingListResponseDto

    @GET("admin/sell-land/field-officers")
    suspend fun getFieldOfficers(): List<AdminFieldOfficerOptionDto>

    @GET("admin/sell-land/cases/assignment-board")
    suspend fun getAssignmentBoard(
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 20
    ): AdminAssignmentBoardResponseDto

    @POST("admin/sell-land/cases/{id}/force-release")
    suspend fun forceReleaseCase(@Path("id") id: Int): AdminForceReleaseResponseDto

    @POST("admin/sell-land/cases/{id}/assign")
    suspend fun assignCase(
        @Path("id") id: Int,
        @Body body: AdminAssignCaseRequestDto
    ): AdminAssignCaseResponseDto

    @GET("admin/sell-land/locked-listings")
    suspend fun getLockedListings(
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 20
    ): AdminLockedListingListResponseDto

    @GET("admin/sell-land/booked-listings")
    suspend fun getBookedListings(
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 20
    ): AdminBookedListingListResponseDto

    @GET("admin/sell-land/sold-listings")
    suspend fun getSoldListings(
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 20
    ): AdminBookedListingListResponseDto

    @GET("admin/sell-land/booked-listings/{id}")
    suspend fun getBookedListingDetail(
        @Path("id") id: Int
    ): AdminBookedListingDetailDto

    @PATCH("admin/sell-land/bookings/{id}/field-officer")
    suspend fun updateBookingFieldOfficer(
        @Path("id") id: Int,
        @Body body: AdminBookingFieldOfficerUpdateRequestDto
    ): AdminBookingFieldOfficerUpdateResponseDto

    @PATCH("admin/sell-land/bookings/{id}/registry-schedule")
    suspend fun scheduleRegistry(
        @Path("id") id: Int,
        @Body body: AdminRegistryScheduleRequestDto
    ): AdminRegistryScheduleResponseDto

    @PATCH("admin/sell-land/bookings/{id}/registry-verify")
    suspend fun verifyRegistry(
        @Path("id") id: Int,
        @Body body: AdminRegistryVerificationRequestDto
    ): AdminRegistryVerificationResponseDto

    @GET("admin/sell-land/bookings/registry-pending")
    suspend fun getRegistryPendingBookings(
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 20
    ): AdminRegistryPendingListResponseDto

    @POST("admin/sell-land/locked-listings/{id}/force-release")
    suspend fun forceReleaseOfferLock(
        @Path("id") id: Int
    ): AdminForceReleaseOfferLockResponseDto

    @GET("admin/sell-land/final-approval")
    suspend fun getFinalApprovalCases(
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 20
    ): AdminFieldVerifiedCaseListResponseDto

    @PATCH("admin/sell-land/final-approval/{id}/action")
    suspend fun finalApprovalAction(
        @Path("id") id: Int,
        @Body body: AdminFinalApprovalActionRequestDto
    ): AdminFinalApprovalActionResponseDto

    @GET("admin/sell-land/refunds/pending-admin")
    suspend fun getPendingAdminRefunds(
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 20
    ): AdminRefundQueueResponseDto

    @PATCH("admin/sell-land/refunds/{id}/forward-accounting")
    suspend fun forwardRefundToAccounting(
        @Path("id") id: Int
    ): AdminForwardRefundResponseDto

    @GET("admin/sell-land/refunds/success")
    suspend fun getSuccessAdminRefunds(
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 20
    ): AdminRefundSuccessListResponseDto

    @GET("ratings/admin/list")
    suspend fun getAdminRatings(
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 50,
        @Query("property_id") propertyId: Int? = null,
        @Query("role") role: String? = null,
        @Query("min_rating") minRating: Int? = null
    ): List<AdminRatingListItemDto>

    @GET("payments/webhook-logs")
    suspend fun getWebhookLogs(
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 50,
        @Query("payment_context") paymentContext: String? = null,
        @Query("status") status: String? = null,
        @Query("event") event: String? = null,
        @Query("order_id") orderId: String? = null,
        @Query("payment_id") paymentId: String? = null
    ): WebhookLogListResponseDto
}
