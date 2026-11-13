package com.example.mybroker_admin.data.remote.api

import com.example.mybroker_admin.data.remote.dto.CreateStaffRequestDto
import com.example.mybroker_admin.data.remote.dto.CreateStaffResponseDto
import com.example.mybroker_admin.data.remote.dto.DeleteStaffResponseDto
import com.example.mybroker_admin.data.remote.dto.ResetPasswordRequestDto

import com.example.mybroker_admin.data.remote.dto.StaffActionResponseDto
import com.example.mybroker_admin.data.remote.dto.StaffDto
import com.example.mybroker_admin.data.remote.dto.ToggleStaffActiveRequestDto
import com.example.mybroker_admin.data.remote.dto.UpdateStaffRequestDto
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path


interface StaffApi {
    @POST("admin/staff")
    suspend fun createStaff(
        @Header("Authorization") bearerToken: String,
        @Body body: CreateStaffRequestDto
    ): CreateStaffResponseDto

    @GET("admin/staff")
    suspend fun getStaffList(
        @Header("Authorization") bearerToken: String
    ): List<StaffDto>

    @PUT("admin/staff/{staffId}")
    suspend fun updateStaff(
        @Header("Authorization") bearerToken: String,
        @Path("staffId") staffId: Int,
        @Body body: UpdateStaffRequestDto
    ): StaffActionResponseDto

    @PATCH("admin/staff/{staffId}/active")
    suspend fun toggleStaffActive(
        @Header("Authorization") bearerToken: String,
        @Path("staffId") staffId: Int,
        @Body body: ToggleStaffActiveRequestDto
    ): StaffActionResponseDto

    @DELETE("admin/staff/{staffId}")
    suspend fun deleteStaff(
        @Header("Authorization") bearerToken: String,
        @Path("staffId") staffId: Int
    ): DeleteStaffResponseDto


    @PUT("admin/staff/{staffId}/reset-password")
    suspend fun resetStaffPassword(
        @Header("Authorization") token: String,
        @Path("staffId") staffId: Int,
        @Body request: ResetPasswordRequestDto
    )


}
