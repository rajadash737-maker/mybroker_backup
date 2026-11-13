package com.example.mybroker_admin.data.repository

import com.example.mybroker_admin.data.remote.api.FieldOfficerApi
import com.example.mybroker_admin.data.remote.dto.FieldOfficerCaseDetailResponse
import com.example.mybroker_admin.data.remote.dto.FieldOfficerReviewRequest
import com.example.mybroker_admin.data.remote.dto.FieldOfficerReviewResponse
import com.example.mybroker_admin.data.remote.dto.VisitPhotoUploadResponse
import okhttp3.MultipartBody

class FieldOfficerRepository(
    private val api: FieldOfficerApi
) {
    suspend fun getDashboard() = api.getDashboard()
    suspend fun getAvailableCases() = api.getAvailableCases()
    suspend fun claimCase(requestId: Int) = api.claimCase(requestId)
    suspend fun releaseCase(requestId: Int) = api.releaseCase(requestId)

    suspend fun getCaseDetail(requestId: Int): FieldOfficerCaseDetailResponse {
        return api.getCaseDetail(requestId)
    }

    suspend fun uploadVisitPhoto(
        requestId: Int,
        filePart: MultipartBody.Part
    ): VisitPhotoUploadResponse {
        return api.uploadVisitPhoto(requestId, filePart)
    }

    suspend fun submitReview(
        requestId: Int,
        decision: String,
        notes: String?,
        rejectReason: String?
    ): FieldOfficerReviewResponse {
        val body = FieldOfficerReviewRequest(
            decision = decision,
            inspection_notes = notes,
            rejection_reason = rejectReason
        )
        return api.submitReview(requestId, body)
    }
}
