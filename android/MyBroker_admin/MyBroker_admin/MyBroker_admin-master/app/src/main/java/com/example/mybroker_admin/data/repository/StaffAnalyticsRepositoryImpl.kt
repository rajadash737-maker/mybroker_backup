package com.example.mybroker_admin.data.repository

import com.example.mybroker_admin.data.remote.api.StaffAnalyticsApi
import com.example.mybroker_admin.data.remote.dto.StaffAnalyticsResponseDto

class StaffAnalyticsRepositoryImpl(
    private val api: StaffAnalyticsApi
) : StaffAnalyticsRepository {

    override suspend fun getStaffAnalytics(
        accessToken: String,
        role: String?,
        range: String?,
        startDate: String?,
        endDate: String?
    ): StaffAnalyticsResponseDto {
        return api.getStaffAnalytics(
            bearerToken = "Bearer $accessToken",
            role = role,
            range = range,
            startDate = startDate,
            endDate = endDate
        )
    }
}
