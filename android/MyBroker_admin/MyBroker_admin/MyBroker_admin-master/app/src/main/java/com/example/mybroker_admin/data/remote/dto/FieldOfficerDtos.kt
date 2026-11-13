package com.example.mybroker_admin.data.remote.dto

import com.google.gson.annotations.SerializedName

data class FieldOfficerDashboardDto(
    @SerializedName("status") val status: String,
    @SerializedName("viewer") val viewer: DashboardViewerDto?,
    @SerializedName("active_case_id") val active_case_id: Int?,
    @SerializedName("active_case") val active_case: FieldOfficerAvailableCaseItemDto?,
    @SerializedName("lock_remaining_seconds") val lock_remaining_seconds: Int?,
    @SerializedName("available_cases") val available_cases: Int,
    @SerializedName("completed_visits") val completed_visits: Int
)

data class FieldOfficerAvailableCaseItemDto(
    @SerializedName("id") val id: Int,
    @SerializedName("owner_name") val owner_name: String?,
    @SerializedName("city") val city: String?,
    @SerializedName("state") val state: String?,
    @SerializedName("pincode") val pincode: String?,
    @SerializedName("location") val location: String?
)

data class FieldOfficerAvailableCaseListDto(
    @SerializedName("total") val total: Int,
    @SerializedName("skip") val skip: Int,
    @SerializedName("limit") val limit: Int,
    @SerializedName("items") val items: List<FieldOfficerAvailableCaseItemDto>
)

data class FieldOfficerCaseActionDto(
    @SerializedName("status") val status: String,
    @SerializedName("request_id") val request_id: Int,
    @SerializedName("lock_expires_at") val lock_expires_at: String?
)

data class FieldOfficerCaseDetailResponse(
    @SerializedName("id") val id: Int,
    @SerializedName("title") val title: String?,
    @SerializedName("owner_name") val owner_name: String?,
    @SerializedName("owner_mobile") val owner_mobile: String?,
    @SerializedName("owner_category") val owner_category: String?,
    @SerializedName("land_type") val land_type: String?,
    @SerializedName("ownership_type") val ownership_type: String?,
    @SerializedName("area") val area: Double?,
    @SerializedName("area_unit") val area_unit: String,
    @SerializedName("city") val city: String?,
    @SerializedName("state") val state: String?,
    @SerializedName("expected_price") val expected_price: Double?,
    @SerializedName("boundary_points") val boundary_points: List<BoundaryPointDto>,
    @SerializedName("seller") val seller: SellerSummaryDto,
    @SerializedName("media") val media: List<ListingMediaDto>,
    @SerializedName("field_officer_visit_photo_url") val field_officer_visit_photo_url: String?
)

data class BoundaryPointDto(
    @SerializedName("lat") val lat: Double,
    @SerializedName("lng") val lng: Double
)

data class SellerSummaryDto(
    @SerializedName("id") val id: Int,
    @SerializedName("fullname") val fullname: String,
    @SerializedName("mobile") val mobile: String,
    @SerializedName("email") val email: String,
    @SerializedName("profile_image_url") val profile_image_url: String?
)

data class ListingMediaDto(
    @SerializedName("id") val id: Int,
    @SerializedName("media_type") val media_type: String,
    @SerializedName("document_type") val document_type: String?,
    @SerializedName("file_url") val file_url: String,
    @SerializedName("file_name") val file_name: String
)

data class VisitPhotoUploadResponse(
    @SerializedName("status") val status: String,
    @SerializedName("request_id") val request_id: Int,
    @SerializedName("visit_photo_url") val visit_photo_url: String
)

data class FieldOfficerReviewRequest(
    @SerializedName("decision") val decision: String,
    @SerializedName("inspection_notes") val inspection_notes: String?,
    @SerializedName("rejection_reason") val rejection_reason: String?
)

data class FieldOfficerReviewResponse(
    @SerializedName("status") val status: String,
    @SerializedName("request_id") val request_id: Int,
    @SerializedName("listing_status") val listing_status: String,
    @SerializedName("field_officer_decision") val field_officer_decision: String,
    @SerializedName("field_officer_reviewed_at") val field_officer_reviewed_at: String,
    @SerializedName("field_officer_rejection_reason") val field_officer_rejection_reason: String?
)


