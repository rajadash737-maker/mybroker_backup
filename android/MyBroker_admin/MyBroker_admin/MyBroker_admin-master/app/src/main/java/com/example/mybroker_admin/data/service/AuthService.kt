package com.example.mybroker_admin.data.service

import com.example.mybroker_admin.data.remote.dto.ChangePasswordResponseDto

interface AuthService {
    suspend fun changePassword(
        role: String,
        email: String,
        oldPassword: String,
        newPassword: String
    ): ChangePasswordResponseDto
}
