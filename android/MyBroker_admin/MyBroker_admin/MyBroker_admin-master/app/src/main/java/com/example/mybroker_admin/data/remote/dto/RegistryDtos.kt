package com.example.mybroker_admin.data.remote.dto

data class RegistryProofDto(
    val id: Int,
    val file_url: String,
    val file_name: String,
    val created_at: String
)

data class FieldOfficerRegistryAssignmentItemDto(
    val booking_id: Int,
    val listing_id: Int,
    val deal_amount: Double?,
    val property_name: String?,
    val property_type: String?,
    val property_area: String?,
    val property_address: String?,
    val buyer_name: String,
    val buyer_mobile: String,
    val seller_name: String?,
    val seller_mobile: String?,
    val registry_date: String?,
    val registry_time: String?,
    val registry_location: String?,
    val status: String,
    val assigned_officer_name: String?,
    val assigned_officer_mobile: String?
)

data class FieldOfficerRegistryAssignmentDetailDto(
    val booking_id: Int,
    val listing_id: Int,
    val deal_amount: Double?,
    val property_name: String?,
    val property_type: String?,
    val property_area: String?,
    val property_address: String?,
    val buyer_name: String,
    val buyer_mobile: String,
    val seller_name: String?,
    val seller_mobile: String?,
    val registry_date: String?,
    val registry_time: String?,
    val registry_location: String?,
    val status: String,
    val assigned_officer_name: String?,
    val assigned_officer_mobile: String?,
    val proofs: List<RegistryProofDto> = emptyList()
)

data class FieldOfficerRegistryAssignmentListResponseDto(
    val total: Int,
    val skip: Int,
    val limit: Int,
    val items: List<FieldOfficerRegistryAssignmentItemDto>
)

data class FieldOfficerRegistryAssignmentDetailResponseDto(
    val status: String,
    val assignment: FieldOfficerRegistryAssignmentDetailDto
)

data class FieldOfficerRegistryProofUploadResponseDto(
    val status: String,
    val booking_id: Int,
    val proofs: List<RegistryProofDto>
)

data class FieldOfficerRegistryCompleteResponseDto(
    val status: String,
    val booking_id: Int,
    val proofs: List<RegistryProofDto>
)
