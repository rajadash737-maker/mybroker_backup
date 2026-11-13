package com.example.mybroker_admin.data.remote.api



import com.example.mybroker_admin.data.remote.dto.FcmTokenRequestDto
import com.example.mybroker_admin.data.remote.dto.FcmTokenResponseDto
import com.example.mybroker_admin.data.remote.dto.ProfilePhotoResponseDto
import com.example.mybroker_admin.data.remote.dto.UpdateProfileRequestDto
import com.example.mybroker_admin.data.remote.dto.UserProfileDto
import okhttp3.MultipartBody
import retrofit2.http.*

interface ProfileApi {

    @GET("users/me/profile")
    suspend fun getMyProfile(): UserProfileDto

    @PUT("users/me/profile")
    suspend fun updateMyProfile(
        @Body body: UpdateProfileRequestDto
    ): UserProfileDto

    @Multipart
    @POST("users/me/profile-photo")
    suspend fun uploadProfilePhoto(
        @Part file: MultipartBody.Part
    ): ProfilePhotoResponseDto

    @POST("users/me/fcm-token")
    suspend fun registerFcmToken(
        @Body body: FcmTokenRequestDto
    ): FcmTokenResponseDto
}
