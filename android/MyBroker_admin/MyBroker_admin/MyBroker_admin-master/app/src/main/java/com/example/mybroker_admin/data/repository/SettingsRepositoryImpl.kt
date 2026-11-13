package com.example.mybroker_admin.data.repository

import com.example.mybroker_admin.data.remote.api.SettingsApi
import com.example.mybroker_admin.data.remote.dto.SocialLinksUpdateRequest
import com.example.mybroker_admin.data.remote.dto.ProcessingFeeUpdateRequest
import okhttp3.MultipartBody

class SettingsRepositoryImpl(
    private val api: SettingsApi
) : SettingsRepository {
    override suspend fun getSocialLinks() = api.getSocialLinks()

    override suspend fun updateSocialLinks(payload: SocialLinksUpdateRequest) =
        api.updateSocialLinks(payload)

    override suspend fun getBanners() = api.getBanners()

    override suspend fun uploadBanner(file: MultipartBody.Part) = api.uploadBanner(file)

    override suspend fun deleteBanner(id: Int) = api.deleteBanner(id)

    override suspend fun getProcessingFees() = api.getProcessingFees()

    override suspend fun updateProcessingFees(payload: ProcessingFeeUpdateRequest) =
        api.updateProcessingFees(payload)
}
