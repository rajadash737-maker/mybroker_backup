package com.example.mybroker_admin.data.service

import com.example.mybroker_admin.data.remote.api.AuthApi
import com.example.mybroker_admin.data.remote.dto.ChangePasswordRequestDto
import com.example.mybroker_admin.data.remote.dto.ChangePasswordResponseDto

class AuthServiceImpl(
    private val authApi: AuthApi
) : AuthService {
    override suspend fun changePassword(
        role: String,
        email: String,
        oldPassword: String,
        newPassword: String
    ): ChangePasswordResponseDto {
        return authApi.changePassword(
            ChangePasswordRequestDto(
                role = role,
                email = email,
                old_password = oldPassword,
                new_password = newPassword
            )
        )
    }
}
