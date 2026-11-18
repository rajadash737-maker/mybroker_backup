package com.example.mybroker_admin.data.remote.api

import retrofit2.Response
import retrofit2.http.GET

data class BackendHealthResponse(val status: String)

interface BackendHealthApi {
    @GET("health")
    suspend fun health(): Response<BackendHealthResponse>
}
