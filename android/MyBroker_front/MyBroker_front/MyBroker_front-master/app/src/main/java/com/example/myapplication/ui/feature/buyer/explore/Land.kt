package com.example.myapplication.ui.feature.buyer.explore

import java.text.NumberFormat
import java.util.Locale
import com.example.myapplication.ui.feature.buyer.utils.formatAreaWithUnit

enum class SortType {
    LATEST,
    PRICE_LOW_TO_HIGH,
    PRICE_HIGH_TO_LOW
}

data class Land(
    val id: Int,
    val title: String,
    val price: Double,
    val priceType: String = "total_price",
    val location: String,
    val city: String?,
    val state: String?,
    val pincode: String?,
    val area: Double,
    val areaUnit: String,
    val images: List<String>,
    val boundaryPoints: List<Pair<Double, Double>> = emptyList(),
    val isVerified: Boolean = true,
    val isFeatured: Boolean = false,
    val isLiked: Boolean = false,
    val likesCount: Int? = null,
    val isLikeUpdating: Boolean = false,
    val isOfferLocked: Boolean = false,
    val offerLockExpiresAt: String? = null,
    val instagramUrl: String? = null,
    val createdAt: String
) {
    val pricePerSqft: Double
        get() = if (area > 0) price / area else 0.0

    val displayAddress: String
        get() = listOfNotNull(city, state, pincode)
            .filter { it.isNotBlank() }
            .joinToString(", ")
            .ifBlank { location }

    val coverImageUrl: String?
        get() = images.firstOrNull()

    val formattedPrice: String
        get() = NumberFormat.getCurrencyInstance(Locale("en", "IN")).format(price)

    val formattedArea: String
        get() = formatAreaWithUnit(area, areaUnit)

    val districtOrCity: String
        get() = city?.takeIf { it.isNotBlank() } ?: "N/A"

    val stateText: String
        get() = state?.takeIf { it.isNotBlank() } ?: "N/A"
}

enum class WishlistHeartStyle { FILLED, OUTLINED }

data class WishlistCardPresentation(
    val heartStyle: WishlistHeartStyle,
    val countLabel: String?
)

fun Land.wishlistCardPresentation() = WishlistCardPresentation(
    heartStyle = if (isLiked) WishlistHeartStyle.FILLED else WishlistHeartStyle.OUTLINED,
    countLabel = likesCount?.coerceAtLeast(0)?.toString()
)

fun Land.withWishlistResult(liked: Boolean, count: Int?): Land = copy(
    isLiked = liked,
    likesCount = count?.coerceAtLeast(0),
    isLikeUpdating = false
)

data class LandFilter(
    val minPrice: Int? = null,
    val maxPrice: Int? = null,
    val minArea: Int? = null,
    val maxArea: Int? = null
)
