package com.example.mybroker_admin.feature.registry.model

import com.example.mybroker_admin.domain.model.RegistryAssignment

data class RegistryDetailUiState(
    val isLoading: Boolean = true,
    val isSubmitting: Boolean = false,
    val error: String? = null,
    val message: String? = null,
    val assignment: RegistryAssignment? = null,
    val dealAmount: String? = null
)
