package com.example.mybroker_admin.feature.fieldofficer.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.repository.FieldOfficerRepository
import com.example.mybroker_admin.feature.fieldofficer.model.FieldCaseUiModel
import com.example.mybroker_admin.feature.fieldofficer.model.FieldDashboardUiState
import com.example.mybroker_admin.feature.fieldofficer.model.FieldStatus
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class FieldDashboardViewModel : ViewModel() {

    private val repository = FieldOfficerRepository(ApiClient.fieldOfficerApi)

    private val _uiState = MutableStateFlow(FieldDashboardUiState())
    val uiState: StateFlow<FieldDashboardUiState> = _uiState

    init {
        loadDashboard()
    }

    fun loadDashboard() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            try {
                val dash = repository.getDashboard()
                val cases = repository.getAvailableCases()

                val active = dash.active_case?.let {
                    FieldCaseUiModel(
                        id = it.id.toString(),
                        sellerName = it.owner_name ?: "-",
                        districtState = "${it.city ?: "-"}, ${it.state ?: "-"}",
                        pincode = it.pincode ?: "-",
                        status = FieldStatus.LOCKED,
                        isLocked = true,
                        lockExpiryTime = System.currentTimeMillis() + ((dash.lock_remaining_seconds ?: 0) * 1000L)
                    )
                }

                val mapped = cases.items.map {
                    FieldCaseUiModel(
                        id = it.id.toString(),
                        sellerName = it.owner_name ?: "-",
                        districtState = "${it.city ?: "-"}, ${it.state ?: "-"}",
                        pincode = it.pincode ?: "-",
                        status = FieldStatus.AVAILABLE
                    )
                }

                val profileUrl = ApiClient.absoluteUrl(
                    dash.viewer?.profileImageUrl?.trim()
                )?.takeIf { it.isNotEmpty() }

                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    activeCase = active,
                    availableCases = mapped,
                    availableCount = dash.available_cases,
                    completedCount = dash.completed_visits,
                    officerName = dash.viewer?.fullname ?: "Field Officer",
                    profileImageUrl = profileUrl,
                    error = null
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message ?: "Failed to load dashboard"
                )
            }
        }
    }

    fun claimCase(case: FieldCaseUiModel) {
        viewModelScope.launch {
            try {
                repository.claimCase(case.id.toInt())
                loadDashboard()
            } catch (_: Exception) {
            }
        }
    }

    fun releaseCase() {
        viewModelScope.launch {
            try {
                val id = _uiState.value.activeCase?.id?.toIntOrNull() ?: return@launch
                repository.releaseCase(id)
                loadDashboard()
            } catch (_: Exception) {
            }
        }
    }
}
