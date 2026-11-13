package com.example.mybroker_admin.feature.profile.changepassword

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.core.session.SessionManager
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.repository.ProfileRepository
import com.example.mybroker_admin.data.repository.ProfileRepositoryImpl
import com.example.mybroker_admin.data.service.AuthService
import com.example.mybroker_admin.data.service.AuthServiceImpl
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import org.json.JSONObject
import retrofit2.HttpException

class ChangePasswordViewModel(
    private val authService: AuthService = AuthServiceImpl(ApiClient.authApi),
    private val profileRepository: ProfileRepository = ProfileRepositoryImpl(ApiClient.profileApi)
) : ViewModel() {

    private val _uiState = MutableStateFlow(
        createState(
            name = SessionManager.currentUserName.orEmpty(),
            role = SessionManager.currentUserRole.orEmpty(),
            email = SessionManager.currentUserEmail.orEmpty()
        )
    )
    val uiState: StateFlow<ChangePasswordUiState> = _uiState.asStateFlow()

    init {
        bootstrapIdentity()
    }

    fun onNameChange(value: String) = updateIdentity { copy(name = value) }
    fun onEmailChange(value: String) = updateIdentity { copy(email = value) }
    fun onCurrentPasswordChange(value: String) = updateIdentity { copy(currentPassword = value) }
    fun onNewPasswordChange(value: String) = updatePasswordStep { copy(newPassword = value) }
    fun onConfirmPasswordChange(value: String) = updatePasswordStep { copy(confirmPassword = value) }

    fun toggleCurrentPasswordVisibility() {
        _uiState.update { it.copy(isCurrentPasswordVisible = !it.isCurrentPasswordVisible) }
    }

    fun toggleNewPasswordVisibility() {
        _uiState.update { it.copy(isNewPasswordVisible = !it.isNewPasswordVisible) }
    }

    fun toggleConfirmPasswordVisibility() {
        _uiState.update { it.copy(isConfirmPasswordVisible = !it.isConfirmPasswordVisible) }
    }

    fun continueToStepTwo() {
        val state = _uiState.value
        val errors = validateStepOne(state)
        if (errors.hasAny()) {
            _uiState.update {
                it.copy(
                    errors = errors,
                    globalMessage = null,
                    canContinue = isStepOneValid(it.copy(errors = errors))
                )
            }
            return
        }

        _uiState.update {
            it.copy(
                step = ChangePasswordStep.SET_NEW_PASSWORD,
                errors = it.errors.copy(newPassword = null, confirmPassword = null),
                globalMessage = null,
                canSubmit = isStepTwoValid(it)
            )
        }
    }

    fun goBackOneStep() {
        _uiState.update {
            when (it.step) {
                ChangePasswordStep.SET_NEW_PASSWORD -> it.copy(
                    step = ChangePasswordStep.VERIFY_IDENTITY,
                    globalMessage = null
                )
                ChangePasswordStep.SUCCESS,
                ChangePasswordStep.VERIFY_IDENTITY -> it
            }
        }
    }

    fun submitChangePassword() {
        val state = _uiState.value
        val errors = validateStepTwo(state)
        if (errors.hasAny()) {
            _uiState.update {
                it.copy(
                    errors = it.errors.copy(
                        newPassword = errors.newPassword,
                        confirmPassword = errors.confirmPassword
                    ),
                    globalMessage = null,
                    canSubmit = false
                )
            }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(isSubmitting = true, globalMessage = null) }

            runCatching {
                authService.changePassword(
                    role = state.roleApi,
                    email = state.email.trim(),
                    oldPassword = state.currentPassword,
                    newPassword = state.newPassword
                )
            }.onSuccess { response ->
                val success = response.message
                    ?: response.detail
                    ?: response.status
                    ?: "Password changed successfully"

                _uiState.update {
                    it.copy(
                        step = ChangePasswordStep.SUCCESS,
                        isSubmitting = false,
                        successMessage = success,
                        logoutRequired = true,
                        globalMessage = null
                    )
                }
            }.onFailure { throwable ->
                _uiState.update {
                    it.copy(
                        isSubmitting = false,
                        globalMessage = parseApiError(throwable, "Unable to change password right now")
                    )
                }
            }
        }
    }

    fun onLogoutHandled() {
        _uiState.update { it.copy(logoutRequired = false) }
    }

    private fun bootstrapIdentity() {
        viewModelScope.launch {
            _uiState.update { it.copy(isBootstrapping = true) }

            runCatching { profileRepository.getMyProfile() }
                .onSuccess { profile ->
                    SessionManager.updateUserIdentity(
                        fullName = profile.fullname,
                        role = profile.role
                    )
                    _uiState.update {
                        createState(
                            name = if (it.name.isBlank()) profile.fullname else it.name,
                            role = profile.role.ifBlank { it.roleRaw },
                            email = it.email
                        ).copy(
                            currentPassword = it.currentPassword,
                            newPassword = it.newPassword,
                            confirmPassword = it.confirmPassword,
                            isCurrentPasswordVisible = it.isCurrentPasswordVisible,
                            isNewPasswordVisible = it.isNewPasswordVisible,
                            isConfirmPasswordVisible = it.isConfirmPasswordVisible,
                            step = it.step,
                            isBootstrapping = false
                        )
                    }
                }
                .onFailure {
                    _uiState.update { current -> current.copy(isBootstrapping = false) }
                }
        }
    }

    private fun updateIdentity(block: ChangePasswordUiState.() -> ChangePasswordUiState) {
        _uiState.update { current ->
            val updated = current.block()
            val identityErrors = if (updated.step == ChangePasswordStep.VERIFY_IDENTITY) {
                validateStepOne(updated, showOnlyFilledErrors = true)
            } else {
                updated.errors.copy(
                    name = validateRequired(updated.name, "Name").takeIf { updated.name.isNotBlank() },
                    email = validateEmail(updated.email),
                    currentPassword = if (updated.currentPassword.isBlank()) null else null
                )
            }

            updated.copy(
                errors = updated.errors.copy(
                    name = identityErrors.name,
                    email = identityErrors.email,
                    currentPassword = if (updated.currentPassword.isBlank()) null else identityErrors.currentPassword
                ),
                globalMessage = null,
                canContinue = isStepOneValid(updated)
            )
        }
    }

    private fun updatePasswordStep(block: ChangePasswordUiState.() -> ChangePasswordUiState) {
        _uiState.update { current ->
            val updated = current.block()
            val passwordErrors = validateStepTwo(updated, showOnlyFilledErrors = true)
            updated.copy(
                errors = updated.errors.copy(
                    newPassword = passwordErrors.newPassword,
                    confirmPassword = passwordErrors.confirmPassword
                ),
                globalMessage = null,
                canSubmit = isStepTwoValid(updated)
            )
        }
    }

    private fun validateStepOne(
        state: ChangePasswordUiState,
        showOnlyFilledErrors: Boolean = false
    ): ChangePasswordFieldErrors {
        return ChangePasswordFieldErrors(
            name = if (showOnlyFilledErrors && state.name.isBlank()) null else validateRequired(state.name, "Name"),
            email = if (showOnlyFilledErrors && state.email.isBlank()) null else validateEmail(state.email),
            currentPassword = if (showOnlyFilledErrors && state.currentPassword.isBlank()) {
                null
            } else {
                validateRequired(state.currentPassword, "Current password")
            }
        )
    }

    private fun validateStepTwo(
        state: ChangePasswordUiState,
        showOnlyFilledErrors: Boolean = false
    ): ChangePasswordFieldErrors {
        val passwordError = if (showOnlyFilledErrors && state.newPassword.isBlank()) {
            null
        } else {
            validatePassword(state.newPassword)
        }

        val confirmError = if (showOnlyFilledErrors && state.confirmPassword.isBlank()) {
            null
        } else if (passwordError == null || state.confirmPassword.isNotBlank()) {
            matchPassword(state.newPassword, state.confirmPassword)
        } else {
            null
        }

        return ChangePasswordFieldErrors(
            newPassword = passwordError,
            confirmPassword = confirmError
        )
    }

    private fun isStepOneValid(state: ChangePasswordUiState): Boolean {
        return validateStepOne(state).hasNone()
    }

    private fun isStepTwoValid(state: ChangePasswordUiState): Boolean {
        return isStepOneValid(state) && validateStepTwo(state).hasNone()
    }

    private fun createState(
        name: String,
        role: String,
        email: String
    ): ChangePasswordUiState {
        val roleApi = normalizeChangePasswordRole(role)
        val roleLabel = formatRoleLabel(role)
        val baseState = ChangePasswordUiState(
            name = name,
            roleRaw = role,
            roleApi = roleApi,
            roleLabel = roleLabel,
            email = email,
            isNameReadOnly = roleApi != "admin" && name.isNotBlank()
        )
        return baseState.copy(
            canContinue = isStepOneValid(baseState),
            canSubmit = isStepTwoValid(baseState)
        )
    }

    private fun ChangePasswordFieldErrors.hasAny(): Boolean {
        return listOf(name, email, currentPassword, newPassword, confirmPassword).any { it != null }
    }

    private fun ChangePasswordFieldErrors.hasNone(): Boolean = !hasAny()

    private fun parseApiError(error: Throwable, fallback: String): String {
        if (error is HttpException) {
            val body = error.response()?.errorBody()?.string().orEmpty()
            val parsed = runCatching {
                val json = JSONObject(body)
                json.optString("detail")
                    .ifBlank { json.optString("message") }
                    .ifBlank { json.optString("status") }
            }.getOrDefault("")

            if (parsed.isNotBlank()) return parsed
            return "HTTP ${error.code()}"
        }
        return error.message ?: fallback
    }
}
