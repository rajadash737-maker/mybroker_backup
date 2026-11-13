package com.example.myapplication.ui.feature.buyer

import com.example.myapplication.ui.feature.buyer.explore.Land
import com.example.myapplication.ui.feature.buyer.explore.WishlistHeartStyle
import com.example.myapplication.ui.feature.buyer.explore.wishlistCardPresentation
import com.example.myapplication.ui.feature.buyer.explore.withWishlistResult
import com.example.myapplication.ui.feature.buyer.data.remote.dto.ExploreLandItemDto
import com.google.gson.Gson
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class WishlistCardPresentationTest {
    @Test
    fun likedCardShowsFilledHeartAndActualCountLabel() {
        val presentation = land(isLiked = true, likesCount = 42).wishlistCardPresentation()

        assertEquals(WishlistHeartStyle.FILLED, presentation.heartStyle)
        assertEquals("42", presentation.countLabel)
    }

    @Test
    fun unlikedCardShowsOutlinedHeartAndNeverInventsMissingCount() {
        val presentation = land(isLiked = false, likesCount = null).wishlistCardPresentation()

        assertEquals(WishlistHeartStyle.OUTLINED, presentation.heartStyle)
        assertNull(presentation.countLabel)
    }

    @Test
    fun successfulLikeAndUnlikeResponsesReplaceStateAndAggregateCount() {
        val initiallyUnliked = land(isLiked = false, likesCount = 8)
        val liked = initiallyUnliked.withWishlistResult(liked = true, count = 9)
        assertTrue(liked.isLiked)
        assertEquals(9, liked.likesCount)

        val unliked = liked.withWishlistResult(liked = false, count = 8)
        assertEquals(false, unliked.isLiked)
        assertEquals(8, unliked.likesCount)
    }

    @Test
    fun exploreDtoReadsBackendAggregateCount() {
        val json = """{"id":1,"title":"Land","land_type":"residential","listing_status":"live","area_unit":"sqft","price_type":"total_price","is_liked":true,"likes_count":17,"created_at":"2026-01-01T00:00:00"}"""

        assertEquals(17, Gson().fromJson(json, ExploreLandItemDto::class.java).likesCount)
    }

    private fun land(isLiked: Boolean, likesCount: Int?) = Land(
        id = 1,
        title = "Land",
        price = 100.0,
        location = "Road",
        city = null,
        state = null,
        pincode = null,
        area = 1.0,
        areaUnit = "acre",
        images = emptyList(),
        isLiked = isLiked,
        likesCount = likesCount,
        createdAt = "2026-01-01"
    )
}
