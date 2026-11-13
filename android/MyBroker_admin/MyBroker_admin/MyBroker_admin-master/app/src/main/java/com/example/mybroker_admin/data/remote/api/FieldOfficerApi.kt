package com.example.mybroker_admin.data.remote.api

import com.example.mybroker_admin.data.remote.dto.FieldOfficerAvailableCaseListDto
import com.example.mybroker_admin.data.remote.dto.FieldOfficerCaseActionDto
import com.example.mybroker_admin.data.remote.dto.FieldOfficerCaseDetailResponse
import com.example.mybroker_admin.data.remote.dto.FieldOfficerDashboardDto
import com.example.mybroker_admin.data.remote.dto.FieldOfficerReviewRequest
import com.example.mybroker_admin.data.remote.dto.FieldOfficerReviewResponse
import com.example.mybroker_admin.data.remote.dto.FieldOfficerRegistryAssignmentDetailResponseDto
import com.example.mybroker_admin.data.remote.dto.FieldOfficerRegistryAssignmentListResponseDto
import com.example.mybroker_admin.data.remote.dto.FieldOfficerRegistryCompleteResponseDto
import com.example.mybroker_admin.data.remote.dto.FieldOfficerRegistryProofUploadResponseDto
import com.example.mybroker_admin.data.remote.dto.VisitPhotoUploadResponse
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query


interface FieldOfficerApi {
    @GET("field-officer/sell-land/dashboard")
    suspend fun getDashboard(): FieldOfficerDashboardDto

    @GET("field-officer/sell-land/cases/available")
    suspend fun getAvailableCases(
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 20
    ): FieldOfficerAvailableCaseListDto

    @POST("field-officer/sell-land/cases/{request_id}/claim")
    suspend fun claimCase(@Path("request_id") requestId: Int): FieldOfficerCaseActionDto

    @POST("field-officer/sell-land/cases/{request_id}/release")
    suspend fun releaseCase(@Path("request_id") requestId: Int): FieldOfficerCaseActionDto


    @GET("field-officer/sell-land/cases/{requestId}")
    suspend fun getCaseDetail(@Path("requestId") requestId: Int): FieldOfficerCaseDetailResponse

    @Multipart
    @POST("field-officer/sell-land/cases/{requestId}/visit-photo")
    suspend fun uploadVisitPhoto(
        @Path("requestId") requestId: Int,
        @Part file: MultipartBody.Part
    ): VisitPhotoUploadResponse

    @PATCH("field-officer/sell-land/cases/{requestId}/review")
    suspend fun submitReview(
        @Path("requestId") requestId: Int,
        @Body body: FieldOfficerReviewRequest
    ): FieldOfficerReviewResponse

    @GET("field-officer/sell-land/registry/assignments")
    suspend fun getRegistryAssignments(
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 20
    ): FieldOfficerRegistryAssignmentListResponseDto

    @GET("field-officer/sell-land/registry/assignments/{bookingId}")
    suspend fun getRegistryAssignmentDetail(
        @Path("bookingId") bookingId: Int
    ): FieldOfficerRegistryAssignmentDetailResponseDto

    @PATCH("field-officer/sell-land/registry/assignments/{bookingId}/start")
    suspend fun startRegistryVisit(
        @Path("bookingId") bookingId: Int
    ): FieldOfficerRegistryAssignmentDetailResponseDto

    @Multipart
    @POST("field-officer/sell-land/registry/assignments/{bookingId}/proofs")
    suspend fun uploadRegistryProofs(
        @Path("bookingId") bookingId: Int,
        @Part files: List<MultipartBody.Part>,
        @Part("notes") notes: RequestBody? = null
    ): FieldOfficerRegistryProofUploadResponseDto

    @PATCH("field-officer/sell-land/registry/assignments/{bookingId}/complete")
    suspend fun completeRegistry(
        @Path("bookingId") bookingId: Int
    ): FieldOfficerRegistryCompleteResponseDto
}
