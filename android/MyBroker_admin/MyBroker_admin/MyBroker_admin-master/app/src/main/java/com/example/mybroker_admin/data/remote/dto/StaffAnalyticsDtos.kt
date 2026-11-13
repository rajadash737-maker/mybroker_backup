package com.example.mybroker_admin.data.remote.dto

data class StaffAnalyticsSummaryDto(
    val total_staff: Int,
    val total_visits: Int,
    val total_verified_docs: Int,
    val total_rejected_docs: Int
)

data class StaffAnalyticsItemDto(
    val id: Int,
    val name: String,
    val mobile: String? = null,
    val role: String,
    val documents_verified: Int? = null,
    val documents_rejected: Int? = null,
    val listings_approved: Int? = null,
    val registry_approved: Int? = null,
    val sold_count: Int? = null,
    val site_visits: Int? = null,
    val registry_visits: Int? = null
)

data class StaffAnalyticsResponseDto(
    val summary: StaffAnalyticsSummaryDto,
    val staff: List<StaffAnalyticsItemDto>
)
