package com.example.mybroker_admin.data.remote.dto

import com.google.gson.annotations.SerializedName

data class DashboardViewerDto(
    @SerializedName("id") val id: Int,
    @SerializedName("fullname") val fullname: String,
    @SerializedName("role") val role: String,
    @SerializedName("profile_image_url") val profileImageUrl: String?
)

data class UserProfileDto(
    @SerializedName("id") val id: Int,
    @SerializedName("fullname") val fullname: String,
    @SerializedName("mobile") val mobile: String?,
    @SerializedName("role") val role: String,
    @SerializedName("profile_image_url") val profileImageUrl: String?,
    @SerializedName("address") val address: String?
)

data class UpdateProfileRequestDto(
    @SerializedName("fullname") val fullname: String,
    @SerializedName("mobile") val mobile: String,
    @SerializedName("address") val address: String
)

data class ProfilePhotoResponseDto(
    @SerializedName("status") val status: String,
    @SerializedName("profile_image_url") val profileImageUrl: String
)
