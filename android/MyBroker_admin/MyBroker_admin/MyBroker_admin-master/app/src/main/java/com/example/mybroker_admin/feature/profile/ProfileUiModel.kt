package com.example.mybroker_admin.feature.profile



data class ProfileUiModel(
    val id: Int = 0,
    val fullName: String = "",
    val mobile: String = "",
    val state: String = "",
    val district: String = "",
    val role: String = "",
    val profileImageUrl: String? = null
)

data class ProfileUiState(
    val isLoading: Boolean = false,
    val isSaving: Boolean = false,
    val message: String? = null,
    val data: ProfileUiModel = ProfileUiModel()
)
