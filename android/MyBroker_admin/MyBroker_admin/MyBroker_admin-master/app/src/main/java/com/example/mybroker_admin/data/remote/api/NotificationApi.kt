package com.example.mybroker_admin.data.remote.api

import com.example.mybroker_admin.data.remote.dto.NotificationListResponseDto
import com.example.mybroker_admin.data.remote.dto.NotificationReadRequestDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

interface NotificationApi {
    @GET("notifications")
    suspend fun listNotifications(): NotificationListResponseDto

    @POST("notifications/read")
    suspend fun markRead(@Body body: NotificationReadRequestDto): NotificationListResponseDto
}
