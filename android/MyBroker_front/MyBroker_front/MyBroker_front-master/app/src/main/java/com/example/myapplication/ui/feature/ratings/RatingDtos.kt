package com.example.myapplication.ui.feature.ratings

import com.google.gson.annotations.SerializedName

data class RatingCreateRequest(
    @SerializedName("property_id") val propertyId: Int,
    val role: String,
    val rating: Int,
    val review: String? = null
)

data class RatingResponse(
    val id: Int,
    @SerializedName("from_user_id") val fromUserId: Int,
    @SerializedName("to_user_id") val toUserId: Int,
    val role: String,
    val rating: Int,
    val review: String? = null,
    @SerializedName("property_id") val propertyId: Int,
    @SerializedName("created_at") val createdAt: String
)

data class RatingSummaryResponse(val average: Double, @SerializedName("total_reviews") val totalReviews: Int)

data class RatingUserSummary(
    val id: Int,
    val fullname: String? = null,
    val mobile: String? = null
)

data class RatingListItemResponse(
    val id: Int,
    val rating: Int,
    val review: String? = null,
    val role: String,
    @SerializedName("property_id") val propertyId: Int,
    @SerializedName("property_title") val propertyTitle: String? = null,
    @SerializedName("listing_code") val listingCode: String? = null,
    @SerializedName("from_user") val fromUser: RatingUserSummary? = null,
    @SerializedName("to_user") val toUser: RatingUserSummary? = null,
    @SerializedName("created_at") val createdAt: String
)
