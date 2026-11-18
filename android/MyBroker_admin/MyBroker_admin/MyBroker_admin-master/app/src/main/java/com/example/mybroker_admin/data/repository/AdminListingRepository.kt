package com.example.mybroker_admin.data.repository

import com.example.mybroker_admin.data.remote.api.AdminListingApi
import com.example.mybroker_admin.data.remote.dto.AdminAssignCaseRequestDto
import com.example.mybroker_admin.data.remote.dto.AdminFinalApprovalActionRequestDto
import com.example.mybroker_admin.data.remote.dto.AdminListingItemDto
import com.example.mybroker_admin.data.remote.dto.AdminInstagramUrlUpdateRequestDto
import com.google.gson.JsonNull
import com.google.gson.JsonPrimitive
import com.example.mybroker_admin.data.remote.dto.AdminBookingFieldOfficerUpdateRequestDto
import com.example.mybroker_admin.data.remote.dto.AdminRegistryScheduleRequestDto
import com.example.mybroker_admin.data.remote.dto.AdminRegistryVerificationRequestDto
import com.example.mybroker_admin.data.remote.dto.ReviewActionRequestDto
import com.example.mybroker_admin.data.remote.dto.WebhookLogListResponseDto
import com.example.mybroker_admin.data.remote.dto.PropertyBookingCancellationPreviewDto
import com.example.mybroker_admin.data.remote.dto.PropertyBookingCancellationRequestDto
import retrofit2.Response

class AdminListingRepository(
    private val api: AdminListingApi
) {
    suspend fun getBookingCancellationPreview(
        bookingId: Int
    ): Response<PropertyBookingCancellationPreviewDto> = api.getBookingCancellationPreview(bookingId)

    suspend fun cancelPropertyBooking(bookingId: Int, decision: String, amount: Double, reason: String) =
        api.cancelPropertyBooking(bookingId, PropertyBookingCancellationRequestDto(decision, amount, reason))

    suspend fun pendingListings(
        state: String? = null,
        district: String? = null
    ): List<AdminListingItemDto> {
        return api.getPending(
            status = "pending",
            state = state,
            district = district,
            skip = 0,
            limit = 20
        ).items
    }

    suspend fun rejectedListings(
        state: String? = null,
        district: String? = null
    ): List<AdminListingItemDto> {
        return api.getRequestsByStatus(
            status = "rejected",
            state = state,
            district = district,
            skip = 0,
            limit = 20
        ).items
    }

    suspend fun getRequestsByStatus(
        status: String,
        state: String? = null,
        district: String? = null
    ): List<AdminListingItemDto> {
        return api.getRequestsByStatus(
            status = status,
            state = state,
            district = district,
            skip = 0,
            limit = 20
        ).items
    }

    suspend fun listingDetail(id: Int) = api.getRequestDetail(id)

    suspend fun updateListingInstagramUrl(id: Int, url: String?) = api.updateListingInstagramUrl(
        id,
        AdminInstagramUrlUpdateRequestDto(url?.let(::JsonPrimitive) ?: JsonNull.INSTANCE)
    )

    suspend fun approve(id: Int) = api.reviewRequest(id, ReviewActionRequestDto("approved"))

    suspend fun reject(id: Int, reason: String) =
        api.reviewRequest(id, ReviewActionRequestDto("rejected", reason))

    suspend fun countByStatus(status: String): Int {
        return api.getRequests(status = status, skip = 0, limit = 1).total
    }

    suspend fun getAllListings(
        skip: Int = 0,
        limit: Int = 50,
        search: String? = null,
        status: String? = null,
        listingId: Int? = null,
        state: String? = null,
        district: String? = null
    ) = api.getAllRequests(
        status = status,
        listingId = listingId,
        skip = skip,
        limit = limit,
        search = search,
        state = state,
        district = district
    )

    suspend fun getAllListingsCount(): Int {
        return api.getAllRequests(skip = 0, limit = 1).total
    }

    suspend fun getWorkflowSummary() = api.getWorkflowSummary()

    suspend fun getAssignmentBoard(skip: Int = 0, limit: Int = 20) =
        api.getAssignmentBoard(skip = skip, limit = limit)

    suspend fun getFieldOfficers() = api.getFieldOfficers()

    suspend fun forceReleaseCase(requestId: Int) =
        api.forceReleaseCase(requestId)

    suspend fun assignCase(requestId: Int, fieldOfficerId: Int, lockHours: Int = 12) =
        api.assignCase(
            id = requestId,
            body = AdminAssignCaseRequestDto(
                field_officer_id = fieldOfficerId,
                lock_hours = lockHours
            )
        )

    suspend fun getLockedListings(skip: Int = 0, limit: Int = 20) =
        api.getLockedListings(skip = skip, limit = limit)

    suspend fun getBookedListings(skip: Int = 0, limit: Int = 20) =
        api.getBookedListings(skip = skip, limit = limit)

    suspend fun getSoldListings(skip: Int = 0, limit: Int = 20) =
        api.getSoldListings(skip = skip, limit = limit)

    suspend fun getBookedListingDetail(id: Int) =
        api.getBookedListingDetail(id)

    suspend fun updateBookingFieldOfficer(bookingId: Int, fieldOfficerId: Int) =
        api.updateBookingFieldOfficer(
            id = bookingId,
            body = AdminBookingFieldOfficerUpdateRequestDto(field_officer_id = fieldOfficerId)
        )

    suspend fun scheduleRegistry(
        bookingId: Int,
        registryDate: String,
        registryTime: String,
        registryLocation: String,
        fieldOfficerId: Int? = null
    ) = run {
        fieldOfficerId?.let {
            api.updateBookingFieldOfficer(
                id = bookingId,
                body = AdminBookingFieldOfficerUpdateRequestDto(field_officer_id = it)
            )
        }
        api.scheduleRegistry(
            id = bookingId,
            body = AdminRegistryScheduleRequestDto(
                registry_date = registryDate,
                registry_time = registryTime,
                registry_location = registryLocation
            )
        )
    }

    suspend fun verifyRegistry(bookingId: Int, decision: String) =
        api.verifyRegistry(
            id = bookingId,
            body = AdminRegistryVerificationRequestDto(decision = decision)
        )

    suspend fun getRegistryPendingBookings(skip: Int = 0, limit: Int = 20) =
        api.getRegistryPendingBookings(skip = skip, limit = limit)

    suspend fun forceReleaseOfferLock(requestId: Int) =
        api.forceReleaseOfferLock(requestId)

    suspend fun getFinalApprovalCases(skip: Int = 0, limit: Int = 20) =
        api.getFinalApprovalCases(skip = skip, limit = limit)

    suspend fun finalApprovalAction(
        requestId: Int,
        decision: String,
        rejectionReason: String? = null
    ) = api.finalApprovalAction(
        id = requestId,
        body = AdminFinalApprovalActionRequestDto(
            decision = decision,
            rejection_reason = rejectionReason
        )
    )

    suspend fun approveGoLive(requestId: Int) =
        finalApprovalAction(requestId, "approve_go_live")

    suspend fun rejectFinal(requestId: Int, reason: String) =
        finalApprovalAction(requestId, "reject", reason)

    suspend fun reassignToFieldOfficer(requestId: Int) =
        finalApprovalAction(requestId, "reassign_to_field_officer")

    suspend fun getPendingAdminRefunds(skip: Int = 0, limit: Int = 20) =
        api.getPendingAdminRefunds(skip = skip, limit = limit)

    suspend fun forwardRefundToAccounting(requestId: Int) =
        api.forwardRefundToAccounting(requestId)

    suspend fun getSuccessAdminRefunds(skip: Int = 0, limit: Int = 20) =
        api.getSuccessAdminRefunds(skip = skip, limit = limit)

    suspend fun getWebhookLogs(
        skip: Int = 0,
        limit: Int = 50,
        paymentContext: String? = null,
        status: String? = null,
        event: String? = null,
        orderId: String? = null,
        paymentId: String? = null
    ): WebhookLogListResponseDto = api.getWebhookLogs(
        skip = skip,
        limit = limit,
        paymentContext = paymentContext,
        status = status,
        event = event,
        orderId = orderId,
        paymentId = paymentId
    )

    suspend fun getWebhookLogsCount(
        paymentContext: String? = null,
        status: String? = null
    ): Int {
        return api.getWebhookLogs(
            skip = 0,
            limit = 1,
            paymentContext = paymentContext,
            status = status
        ).total
    }
}
