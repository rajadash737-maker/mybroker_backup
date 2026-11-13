package com.example.mybroker_admin.data.remote.dto



data class LoginRequestDto(
    val identifier: String,
    val password: String
)

data class RefreshRequestDto(
    val refresh_token: String
)

data class AuthResponseDto(
    val status: String,
    val dashboard_key: String?,
    val user: AuthUserDto?,
    val tokens: TokenPairDto?
)

data class AuthUserDto(
    val id: Int,
    val fullname: String,
    val email: String,
    val role: String,
    val is_active: Boolean
)

data class ChangePasswordRequestDto(
    val role: String,
    val email: String,
    val old_password: String,
    val new_password: String
)

data class ChangePasswordResponseDto(
    val status: String? = null,
    val message: String? = null,
    val detail: String? = null
)

data class TokenPairDto(
    val access_token: String,
    val refresh_token: String,
    val token_type: String
)
