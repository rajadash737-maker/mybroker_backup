package com.example.mybroker_admin.data.repository

import com.example.mybroker_admin.data.remote.dto.BannerDeleteResponse
import com.example.mybroker_admin.data.remote.dto.BannerDto
import com.example.mybroker_admin.data.remote.dto.ProcessingFeeSettingsDto
import com.example.mybroker_admin.data.remote.dto.ProcessingFeeUpdateRequest
import com.example.mybroker_admin.data.remote.dto.SocialLinksDto
import com.example.mybroker_admin.data.remote.dto.SocialLinksUpdateRequest
import okhttp3.MultipartBody

interface SettingsRepository {
    suspend fun getSocialLinks(): SocialLinksDto
    suspend fun updateSocialLinks(payload: SocialLinksUpdateRequest): SocialLinksDto
    suspend fun getBanners(): List<BannerDto>
    suspend fun uploadBanner(file: MultipartBody.Part): BannerDto
    suspend fun deleteBanner(id: Int): BannerDeleteResponse
    suspend fun getProcessingFees(): ProcessingFeeSettingsDto
    suspend fun updateProcessingFees(payload: ProcessingFeeUpdateRequest): ProcessingFeeSettingsDto
}
