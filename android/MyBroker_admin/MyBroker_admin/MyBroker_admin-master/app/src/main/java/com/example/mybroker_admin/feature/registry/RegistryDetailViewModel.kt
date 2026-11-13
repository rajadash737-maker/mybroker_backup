package com.example.mybroker_admin.feature.registry

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.repository.RegistryAssignmentRepositoryImpl
import com.example.mybroker_admin.domain.repository.RegistryAssignmentRepository
import com.example.mybroker_admin.feature.registry.model.RegistryDetailUiState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import okhttp3.MultipartBody
import java.text.DecimalFormat

class RegistryDetailViewModel(
    private val repository: RegistryAssignmentRepository = RegistryAssignmentRepositoryImpl(
        fieldOfficerApi = ApiClient.fieldOfficerApi,
        adminListingApi = ApiClient.adminListingApi
    )
) : ViewModel() {

    private val _uiState = MutableStateFlow(RegistryDetailUiState())
    val uiState: StateFlow<RegistryDetailUiState> = _uiState

    private var assignmentId: String? = null

    fun load(id: String) {
        assignmentId = id
        _uiState.value = _uiState.value.copy(isLoading = true, error = null)
        viewModelScope.launch {
            runCatching { repository.getAssignment(id) }
                .onSuccess { item ->
                    val dealAmount = formatPrice(item?.dealAmount)
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        assignment = item,
                        dealAmount = dealAmount,
                        error = if (item == null) "Registry assignment not found" else null
                    )
                }
                .onFailure { e ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = e.message ?: "Failed to load registry"
                    )
                }
        }
    }

    fun scheduleRegistry(date: String, time: String, location: String, officer: String) {
        val id = assignmentId ?: return
        val officerId = officer.toIntOrNull()
        submitAction("Registry scheduled") {
            repository.scheduleRegistry(
                bookingId = id,
                date = date,
                time = time,
                location = location,
                fieldOfficerId = officerId
            )
        }
    }

    fun startVisit() {
        val id = assignmentId ?: return
        submitAction("Visit started") {
            repository.startVisit(id)
        }
    }

    fun completeTask() {
        val id = assignmentId ?: return
        submitAction("Task completed") {
            repository.completeTask(id)
        }
    }

    fun uploadProofs(parts: List<MultipartBody.Part>) {
        val id = assignmentId ?: return
        submitAction("Proof uploaded") {
            repository.uploadProofs(id, parts)
        }
    }

    fun clearMessage() {
        _uiState.value = _uiState.value.copy(message = null)
    }

    private fun submitAction(message: String, action: suspend () -> Unit) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isSubmitting = true, error = null)
            try {
                action()
                val refreshed = assignmentId?.let { repository.getAssignment(it) }
                val dealAmount = formatPrice(refreshed?.dealAmount)
                _uiState.value = _uiState.value.copy(
                    isSubmitting = false,
                    message = message,
                    assignment = refreshed ?: _uiState.value.assignment,
                    dealAmount = dealAmount ?: _uiState.value.dealAmount
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isSubmitting = false,
                    error = e.message ?: "Action failed"
                )
            }
        }
    }

    private fun formatPrice(value: Double?): String? {
        if (value == null || value <= 0.0) return null
        return "\u20B9 ${DecimalFormat("#,##0.##").format(value)}"
    }
}
