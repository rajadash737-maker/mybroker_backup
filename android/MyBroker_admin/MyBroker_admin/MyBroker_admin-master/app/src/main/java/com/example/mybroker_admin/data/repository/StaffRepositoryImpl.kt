package com.example.mybroker_admin.data.repository

import com.example.mybroker_admin.data.remote.api.StaffApi
import com.example.mybroker_admin.data.remote.dto.CreateStaffRequestDto
import com.example.mybroker_admin.data.remote.dto.CreateStaffResponseDto
import com.example.mybroker_admin.data.remote.dto.DeleteStaffResponseDto
import com.example.mybroker_admin.data.remote.dto.ResetPasswordRequestDto


import com.example.mybroker_admin.data.remote.dto.StaffActionResponseDto
import com.example.mybroker_admin.data.remote.dto.StaffDto
import com.example.mybroker_admin.data.remote.dto.ToggleStaffActiveRequestDto
import com.example.mybroker_admin.data.remote.dto.UpdateStaffRequestDto

class StaffRepositoryImpl(
    private val api: StaffApi
) : StaffRepository {

    override suspend fun createStaff(
        accessToken: String,
        fullname: String,
        email: String,
        password: String,
        role: String
    ): CreateStaffResponseDto {
        return api.createStaff(
            bearerToken = "Bearer $accessToken",
            body = CreateStaffRequestDto(fullname, email, password, role)
        )
    }

    override suspend fun getStaffList(accessToken: String): List<StaffDto> {
        return api.getStaffList("Bearer $accessToken")
    }

    override suspend fun updateStaff(
        accessToken: String,
        staffId: Int,
        fullname: String,
        email: String,
        role: String
    ): StaffActionResponseDto {
        return api.updateStaff(
            bearerToken = "Bearer $accessToken",
            staffId = staffId,
            body = UpdateStaffRequestDto(
                fullname = fullname,
                email = email,
                role = role
            )
        )
    }


    override suspend fun toggleStaffActive(
        accessToken: String,
        staffId: Int,
        isActive: Boolean
    ): StaffActionResponseDto {
        return api.toggleStaffActive(
            bearerToken = "Bearer $accessToken",
            staffId = staffId,
            body = ToggleStaffActiveRequestDto(is_active = isActive)
        )
    }

    override suspend fun deleteStaff(
        accessToken: String,
        staffId: Int
    ): DeleteStaffResponseDto {
        return api.deleteStaff(
            bearerToken = "Bearer $accessToken",
            staffId = staffId
        )
    }


    override suspend fun resetStaffPassword(
        accessToken: String,
        staffId: Int,
        newPassword: String
    ) {
        api.resetStaffPassword(
            token = "Bearer $accessToken",
            staffId = staffId,
            request = ResetPasswordRequestDto(new_password = newPassword)
        )
    }




}
