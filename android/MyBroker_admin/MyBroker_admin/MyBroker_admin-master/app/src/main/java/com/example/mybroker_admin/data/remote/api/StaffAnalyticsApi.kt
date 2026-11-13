package com.example.mybroker_admin.data.remote.api

import com.example.mybroker_admin.data.remote.dto.StaffAnalyticsResponseDto
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Query

interface StaffAnalyticsApi {
    @GET("admin/staff/analytics")
    suspend fun getStaffAnalytics(
        @Header("Authorization") bearerToken: String,
        @Query("role") role: String? = null,
        @Query("range") range: String? = null,
        @Query("start_date") startDate: String? = null,
        @Query("end_date") endDate: String? = null
    ): StaffAnalyticsResponseDto
}
