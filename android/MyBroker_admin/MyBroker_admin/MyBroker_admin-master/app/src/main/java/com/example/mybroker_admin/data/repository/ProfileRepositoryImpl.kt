package com.example.mybroker_admin.data.repository



import com.example.mybroker_admin.data.remote.api.ProfileApi
import com.example.mybroker_admin.data.remote.dto.UpdateProfileRequestDto
import okhttp3.MultipartBody

class ProfileRepositoryImpl(
    private val api: ProfileApi
) : ProfileRepository {

    override suspend fun getMyProfile() = api.getMyProfile()

    override suspend fun updateMyProfile(
        fullname: String,
        mobile: String,
        address: String
    ) = api.updateMyProfile(
        UpdateProfileRequestDto(
            fullname = fullname,
            mobile = mobile,
            address = address
        )
    )

    override suspend fun uploadProfilePhoto(filePart: MultipartBody.Part): String {
        return api.uploadProfilePhoto(filePart).profileImageUrl
    }
}
