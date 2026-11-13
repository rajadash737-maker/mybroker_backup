package com.example.mybroker_admin.data.repository



import com.example.mybroker_admin.data.remote.api.AuthApi

import com.example.mybroker_admin.data.remote.dto.LoginRequestDto
import com.example.mybroker_admin.domain.model.LoginResult

class AuthRepositoryImpl(
    private val api: AuthApi
) : AuthRepository {
    override suspend fun login(identifier: String, password: String): LoginResult {
        val res = api.login(LoginRequestDto(identifier, password))
        return LoginResult(
            status = res.status,
            dashboardKey = res.dashboard_key,
            role = res.user?.role,
            fullName = res.user?.fullname,
            email = res.user?.email,
            accessToken = res.tokens?.access_token,
            refreshToken = res.tokens?.refresh_token
        )
    }
}

