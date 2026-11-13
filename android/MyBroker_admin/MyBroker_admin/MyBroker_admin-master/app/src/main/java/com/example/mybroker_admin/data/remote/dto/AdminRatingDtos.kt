package com.example.mybroker_admin.data.remote.dto

import com.google.gson.annotations.SerializedName

data class AdminRatingUserDto(
    @SerializedName("id") val id: Int,
    @SerializedName("fullname") val fullname: String? = null,
    @SerializedName("mobile") val mobile: String? = null
)

data class AdminRatingListItemDto(
    @SerializedName("id") val id: Int,
    @SerializedName("rating") val rating: Int,
    @SerializedName("review") val review: String? = null,
    @SerializedName("role") val role: String,
    @SerializedName("property_id") val propertyId: Int,
    @SerializedName("property_title") val propertyTitle: String? = null,
    @SerializedName("listing_code") val listingCode: String? = null,
    @SerializedName("from_user") val fromUser: AdminRatingUserDto? = null,
    @SerializedName("to_user") val toUser: AdminRatingUserDto? = null,
    @SerializedName("created_at") val createdAt: String
)
