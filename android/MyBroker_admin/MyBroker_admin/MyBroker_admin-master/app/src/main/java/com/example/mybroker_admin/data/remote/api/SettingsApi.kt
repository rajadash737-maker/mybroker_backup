package com.example.mybroker_admin.data.remote.api

import com.example.mybroker_admin.data.remote.dto.BannerDeleteResponse
import com.example.mybroker_admin.data.remote.dto.BannerDto
import com.example.mybroker_admin.data.remote.dto.ProcessingFeeSettingsDto
import com.example.mybroker_admin.data.remote.dto.ProcessingFeeUpdateRequest
import com.example.mybroker_admin.data.remote.dto.SocialLinksDto
import com.example.mybroker_admin.data.remote.dto.SocialLinksUpdateRequest
import okhttp3.MultipartBody
import retrofit2.http.DELETE
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.PUT

interface SettingsApi {
    @GET("settings/social-links")
    suspend fun getSocialLinks(): SocialLinksDto

    @PUT("settings/social-links")
    suspend fun updateSocialLinks(
        @Body body: SocialLinksUpdateRequest
    ): SocialLinksDto

    @GET("settings/banners")
    suspend fun getBanners(): List<BannerDto>

    @Multipart
    @POST("settings/banners")
    suspend fun uploadBanner(
        @Part file: MultipartBody.Part
    ): BannerDto

    @DELETE("settings/banners/{id}")
    suspend fun deleteBanner(
        @Path("id") id: Int
    ): BannerDeleteResponse

    @GET("settings/processing-fees")
    suspend fun getProcessingFees(): ProcessingFeeSettingsDto

    @PUT("settings/processing-fees")
    suspend fun updateProcessingFees(
        @Body body: ProcessingFeeUpdateRequest
    ): ProcessingFeeSettingsDto
}
