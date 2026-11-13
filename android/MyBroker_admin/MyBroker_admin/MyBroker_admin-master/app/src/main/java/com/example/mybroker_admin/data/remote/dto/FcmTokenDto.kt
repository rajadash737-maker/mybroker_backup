package com.example.mybroker_admin.data.remote.dto

data class FcmTokenRequestDto(
    val token: String
)

data class FcmTokenResponseDto(
    val status: String? = null
)
