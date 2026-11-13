package com.example.mybroker_admin.data.remote.dto

data class CreateStaffRequestDto(
    val fullname: String,
    val email: String,
    val password: String,
    val role: String
)

data class UpdateStaffRequestDto(
    val fullname: String,
    val email: String,
    val role: String
)

data class ToggleStaffActiveRequestDto(
    val is_active: Boolean
)

data class StaffDto(
    val id: Int,
    val fullname: String,
    val email: String,
    val role: String,
    val is_active: Boolean,
    val username: String? = null,
    val mobile: String? = null,
    val created_at: String? = null
)

data class CreateStaffResponseDto(
    val status: String,
    val staff: StaffDto
)

data class StaffActionResponseDto(
    val status: String,
    val staff: StaffDto
)

data class DeleteStaffResponseDto(
    val status: String
)

data class ResetPasswordRequestDto(
    val new_password: String
)

