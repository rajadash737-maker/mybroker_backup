package com.example.mybroker_admin.domain.model



data class LoginResult(
    val status: String,
    val dashboardKey: String?,
    val role: String?,
    val fullName: String?,
    val email: String?,
    val accessToken: String?,
    val refreshToken: String?
)
