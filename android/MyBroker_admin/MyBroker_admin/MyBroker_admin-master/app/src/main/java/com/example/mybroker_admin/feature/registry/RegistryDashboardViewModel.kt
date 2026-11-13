package com.example.mybroker_admin.feature.registry

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.repository.RegistryAssignmentRepositoryImpl
import com.example.mybroker_admin.domain.model.RegistryStatus
import com.example.mybroker_admin.domain.repository.RegistryAssignmentRepository
import com.example.mybroker_admin.feature.registry.model.RegistryDashboardUiState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class RegistryDashboardViewModel(
    private val repository: RegistryAssignmentRepository = RegistryAssignmentRepositoryImpl(
        fieldOfficerApi = ApiClient.fieldOfficerApi,
        adminListingApi = ApiClient.adminListingApi
    )
) : ViewModel() {

    private val _uiState = MutableStateFlow(RegistryDashboardUiState())
    val uiState: StateFlow<RegistryDashboardUiState> = _uiState

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            runCatching { repository.getAssignments() }
                .onSuccess { list ->
                    val upcoming = list
                        .filter { it.status != RegistryStatus.COMPLETED }
                        .minByOrNull { statusOrder(it.status) }
                    _uiState.value = RegistryDashboardUiState(
                        isLoading = false,
                        error = null,
                        upcoming = upcoming,
                        items = list.filter { it.status != RegistryStatus.COMPLETED }
                    )
                }
                .onFailure { e ->
                    _uiState.value = RegistryDashboardUiState(
                        isLoading = false,
                        error = e.message ?: "Failed to load registry",
                        items = emptyList()
                    )
                }
        }
    }

    private fun statusOrder(status: RegistryStatus): Int {
        return when (status) {
            RegistryStatus.SCHEDULED -> 0
            RegistryStatus.IN_PROGRESS -> 1
            RegistryStatus.BOOKED -> 2
            RegistryStatus.COMPLETED -> 3
        }
    }
}
