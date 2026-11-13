package com.example.mybroker_admin.feature.registry.model

import com.example.mybroker_admin.domain.model.RegistryAssignment

data class RegistryDashboardUiState(
    val isLoading: Boolean = true,
    val error: String? = null,
    val upcoming: RegistryAssignment? = null,
    val items: List<RegistryAssignment> = emptyList()
)
