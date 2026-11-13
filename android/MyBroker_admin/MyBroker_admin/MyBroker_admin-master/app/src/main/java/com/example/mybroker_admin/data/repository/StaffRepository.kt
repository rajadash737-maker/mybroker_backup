package com.example.mybroker_admin.data.repository

import com.example.mybroker_admin.data.remote.dto.CreateStaffResponseDto
import com.example.mybroker_admin.data.remote.dto.DeleteStaffResponseDto

import com.example.mybroker_admin.data.remote.dto.StaffActionResponseDto
import com.example.mybroker_admin.data.remote.dto.StaffDto

interface StaffRepository {
    suspend fun createStaff(
        accessToken: String,
        fullname: String,
        email: String,
        password: String,
        role: String
    ): CreateStaffResponseDto

    suspend fun getStaffList(accessToken: String): List<StaffDto>

    suspend fun updateStaff(
        accessToken: String,
        staffId: Int,
        fullname: String,
        email: String,
        role: String
    ): StaffActionResponseDto


    suspend fun toggleStaffActive(
        accessToken: String,
        staffId: Int,
        isActive: Boolean
    ): StaffActionResponseDto

    suspend fun deleteStaff(
        accessToken: String,
        staffId: Int
    ): DeleteStaffResponseDto


    suspend fun resetStaffPassword(
        accessToken: String,
        staffId: Int,
        newPassword: String
    )


}
