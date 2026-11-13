package com.example.mybroker_admin.feature.superadmin.staffanalytics.model

enum class StaffAnalyticsRoleTab {
    ALL,
    ADMIN,
    FIELD_OFFICER
}

enum class StaffAnalyticsDateFilter {
    ALL,
    TODAY,
    WEEK,
    MONTH,
    CUSTOM
}

data class StaffAnalyticsSummary(
    val totalStaffCount: Int = 0,
    val totalSiteVisits: Int = 0,
    val totalVerifiedDocuments: Int = 0,
    val totalRejectedDocuments: Int = 0
)

data class StaffAnalyticsItem(
    val id: Int,
    val name: String,
    val mobile: String?,
    val role: String,
    val documentsVerifiedCount: Int = 0,
    val documentsRejectedCount: Int = 0,
    val listingsApproved: Int = 0,
    val registryApprovedCount: Int = 0,
    val soldCount: Int = 0,
    val siteVisitsCount: Int = 0,
    val registryVisitsCount: Int = 0
)

data class StaffAnalyticsUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val summary: StaffAnalyticsSummary = StaffAnalyticsSummary(),
    val staff: List<StaffAnalyticsItem> = emptyList(),
    val selectedRoleTab: StaffAnalyticsRoleTab = StaffAnalyticsRoleTab.ALL,
    val dateFilter: StaffAnalyticsDateFilter = StaffAnalyticsDateFilter.TODAY,
    val customStart: String = "",
    val customEnd: String = "",
    val filterMessage: String? = null
)
