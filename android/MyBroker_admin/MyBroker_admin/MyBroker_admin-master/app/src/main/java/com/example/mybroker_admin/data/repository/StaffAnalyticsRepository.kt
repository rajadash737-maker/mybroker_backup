package com.example.mybroker_admin.data.repository

import com.example.mybroker_admin.data.remote.dto.StaffAnalyticsResponseDto

interface StaffAnalyticsRepository {
    suspend fun getStaffAnalytics(
        accessToken: String,
        role: String? = null,
        range: String? = null,
        startDate: String? = null,
        endDate: String? = null
    ): StaffAnalyticsResponseDto
}
