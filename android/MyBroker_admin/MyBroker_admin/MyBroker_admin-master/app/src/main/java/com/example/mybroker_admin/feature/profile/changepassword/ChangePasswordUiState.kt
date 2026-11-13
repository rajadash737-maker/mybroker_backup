package com.example.mybroker_admin.feature.profile.changepassword

enum class ChangePasswordStep {
    VERIFY_IDENTITY,
    SET_NEW_PASSWORD,
    SUCCESS
}

data class ChangePasswordFieldErrors(
    val name: String? = null,
    val email: String? = null,
    val currentPassword: String? = null,
    val newPassword: String? = null,
    val confirmPassword: String? = null
)

data class ChangePasswordUiState(
    val step: ChangePasswordStep = ChangePasswordStep.VERIFY_IDENTITY,
    val isBootstrapping: Boolean = false,
    val isSubmitting: Boolean = false,
    val name: String = "",
    val roleRaw: String = "",
    val roleLabel: String = "",
    val roleApi: String = "",
    val email: String = "",
    val currentPassword: String = "",
    val newPassword: String = "",
    val confirmPassword: String = "",
    val isNameReadOnly: Boolean = false,
    val isCurrentPasswordVisible: Boolean = false,
    val isNewPasswordVisible: Boolean = false,
    val isConfirmPasswordVisible: Boolean = false,
    val errors: ChangePasswordFieldErrors = ChangePasswordFieldErrors(),
    val canContinue: Boolean = false,
    val canSubmit: Boolean = false,
    val globalMessage: String? = null,
    val successMessage: String? = null,
    val logoutRequired: Boolean = false
)
