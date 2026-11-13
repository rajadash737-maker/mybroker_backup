package com.example.mybroker_admin.feature.fieldofficer.model



data class FieldDashboardUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val activeCase: FieldCaseUiModel? = null,
    val availableCases: List<FieldCaseUiModel> = emptyList(),
    val availableCount: Int = 0,
    val completedCount: Int = 0,
    val officerName: String = "Field Officer",
    val profileImageUrl: String? = null
)
