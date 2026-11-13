package com.example.mybroker_admin.data.remote.api

import com.example.mybroker_admin.data.remote.dto.AuthResponseDto
import com.example.mybroker_admin.data.remote.dto.ChangePasswordRequestDto
import com.example.mybroker_admin.data.remote.dto.ChangePasswordResponseDto
import com.example.mybroker_admin.data.remote.dto.LoginRequestDto
import com.example.mybroker_admin.data.remote.dto.RefreshRequestDto
import retrofit2.http.Body
import retrofit2.http.POST

interface AuthApi {
    @POST("auth/login")
    suspend fun login(@Body body: LoginRequestDto): AuthResponseDto

    @POST("auth/refresh")
    suspend fun refresh(@Body body: RefreshRequestDto): AuthResponseDto

    @POST("auth/change-password")
    suspend fun changePassword(@Body body: ChangePasswordRequestDto): ChangePasswordResponseDto
}
