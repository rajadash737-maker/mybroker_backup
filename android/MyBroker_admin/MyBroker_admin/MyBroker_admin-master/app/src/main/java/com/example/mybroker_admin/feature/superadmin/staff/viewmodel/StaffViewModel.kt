package com.example.mybroker_admin.feature.superadmin.staff.viewmodel

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.core.model.UserRole
import com.example.mybroker_admin.core.session.SessionManager
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.remote.dto.StaffDto
import com.example.mybroker_admin.data.repository.StaffRepositoryImpl
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class CreateStaffUiState(
    val isLoading: Boolean = false,
    val isSuccess: Boolean = false,
    val error: String? = null
)

data class StaffListUiState(
    val isLoading: Boolean = false,
    val isActionLoading: Boolean = false,
    val data: List<StaffDto> = emptyList(),
    val error: String? = null,
    val successMessage: String? = null
)

class StaffViewModel : ViewModel() {

    private val repo = StaffRepositoryImpl(ApiClient.staffApi)

    private val _createState = MutableStateFlow(CreateStaffUiState())
    val createState: StateFlow<CreateStaffUiState> = _createState

    private val _listState = MutableStateFlow(StaffListUiState())
    val listState: StateFlow<StaffListUiState> = _listState

    fun createStaff(name: String, email: String, password: String, role: UserRole) {
        val token = SessionManager.accessToken
        if (token.isNullOrBlank()) {
            _createState.update { it.copy(error = "Session expired. Login again.") }
            return
        }

        _createState.update { it.copy(isLoading = true, isSuccess = false, error = null) }

        viewModelScope.launch {
            try {
                repo.createStaff(token, name.trim(), email.trim(), password, role.name)
                _createState.update { it.copy(isLoading = false, isSuccess = true) }
            } catch (e: Exception) {
                _createState.update { it.copy(isLoading = false, error = e.message ?: "Create staff failed") }
            }
        }
    }

    fun loadStaff() {
        val token = SessionManager.accessToken
        if (token.isNullOrBlank()) {
            _listState.update { it.copy(error = "Session expired. Login again.") }
            return
        }

        _listState.update { it.copy(isLoading = true, error = null) }

        viewModelScope.launch {
            try {
                val staff = repo.getStaffList(token)
                _listState.update { it.copy(isLoading = false, data = staff) }
            } catch (e: Exception) {
                _listState.update { it.copy(isLoading = false, error = e.message ?: "Failed to load staff") }
            }
        }
    }

    fun resetCreateState() {
        _createState.value = CreateStaffUiState()
    }

    fun deleteStaff(staffId: Int) {
        val token = SessionManager.accessToken ?: return

        viewModelScope.launch {
            try {
                repo.deleteStaff(token, staffId)
                _listState.update { state ->
                    state.copy(
                        data = state.data.filterNot { it.id == staffId },
                        successMessage = "Staff deleted"
                    )
                }

            } catch (e: Exception) {
                _listState.update { it.copy(error = e.message ?: "Delete failed") }
            }
        }
    }

    fun toggleActive(staffId: Int, currentIsActive: Boolean) {
        val token = SessionManager.accessToken ?: return

        _listState.update { it.copy(isActionLoading = true) }

        viewModelScope.launch {
            try {
                repo.toggleStaffActive(
                    accessToken = token,
                    staffId = staffId,
                    isActive = !currentIsActive
                )

                _listState.update { state ->
                    state.copy(
                        isActionLoading = false,
                        successMessage = "Status updated",
                        data = state.data.map {
                            if (it.id == staffId)
                                it.copy(is_active = !currentIsActive)
                            else it
                        }
                    )
                }

            } catch (e: Exception) {
                _listState.update {
                    it.copy(
                        isActionLoading = false,
                        error = e.message ?: "Update failed"
                    )
                }
            }
        }
    }


    fun updateStaff(staffId: Int, name: String, email: String, role: UserRole) {
        val token = SessionManager.accessToken ?: return

        _listState.update { it.copy(isActionLoading = true, error = null, successMessage = null) }

        viewModelScope.launch {
            try {
                repo.updateStaff(
                    accessToken = token,
                    staffId = staffId,
                    fullname = name.trim(),
                    email = email.trim(),
                    role = role.name
                )
                _listState.update {
                    it.copy(
                        isActionLoading = false,
                        successMessage = "Staff updated successfully"
                    )
                }
                loadStaff()
            } catch (e: Exception) {
                val msg = if (e.message?.contains("Email already in use", true) == true) {
                    "Email already in use"
                } else {
                    e.message ?: "Update failed"
                }
                _listState.update { it.copy(isActionLoading = false, error = msg) }
            }
        }
    }

    fun resetStaffPassword(staffId: Int, newPassword: String) {

        val token = SessionManager.accessToken
        if (token.isNullOrBlank()) {
            _listState.update { it.copy(error = "Session expired. Login again.") }
            return
        }

        _listState.update { it.copy(isActionLoading = true, error = null, successMessage = null) }

        viewModelScope.launch {
            try {
                repo.resetStaffPassword(token, staffId, newPassword)

                _listState.update {
                    it.copy(
                        isActionLoading = false,
                        successMessage = "Password updated successfully"
                    )
                }

            } catch (e: Exception) {
                _listState.update {
                    it.copy(
                        isActionLoading = false,
                        error = e.message ?: "Reset password failed"
                    )
                }
            }
        }
    }

    fun clearMessages() {
        _listState.update { it.copy(successMessage = null, error = null) }
    }



}
