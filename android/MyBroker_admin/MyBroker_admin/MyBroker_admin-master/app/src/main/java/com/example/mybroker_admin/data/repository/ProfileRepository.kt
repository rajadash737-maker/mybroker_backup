package com.example.mybroker_admin.data.repository



import com.example.mybroker_admin.data.remote.dto.UserProfileDto
import okhttp3.MultipartBody

interface ProfileRepository {
    suspend fun getMyProfile(): UserProfileDto
    suspend fun updateMyProfile(fullname: String, mobile: String, address: String): UserProfileDto
    suspend fun uploadProfilePhoto(filePart: MultipartBody.Part): String
}
