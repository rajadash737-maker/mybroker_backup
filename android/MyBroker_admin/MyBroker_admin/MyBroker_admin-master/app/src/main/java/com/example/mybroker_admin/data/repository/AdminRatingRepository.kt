package com.example.mybroker_admin.data.repository

import com.example.mybroker_admin.data.remote.api.AdminListingApi
import com.example.mybroker_admin.data.remote.dto.AdminRatingListItemDto

class AdminRatingRepository(
    private val api: AdminListingApi
) {
    suspend fun getRatings(
        skip: Int = 0,
        limit: Int = 50,
        propertyId: Int? = null,
        role: String? = null,
        minRating: Int? = null
    ): List<AdminRatingListItemDto> {
        return api.getAdminRatings(
            skip = skip,
            limit = limit,
            propertyId = propertyId,
            role = role,
            minRating = minRating
        )
    }
}
