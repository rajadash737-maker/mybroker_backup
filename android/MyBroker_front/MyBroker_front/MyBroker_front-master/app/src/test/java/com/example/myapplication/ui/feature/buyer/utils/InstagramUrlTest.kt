package com.example.myapplication.ui.feature.buyer.utils

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import com.google.gson.Gson
import com.example.myapplication.ui.feature.buyer.data.remote.dto.ExploreLandItemDto

class InstagramUrlTest {
    @Test fun acceptsProfilePostAndReelUrls() {
        assertEquals("https://instagram.com/name/", validatedInstagramUrl("https://instagram.com/name/"))
        assertEquals("https://www.instagram.com/p/abc_123/", validatedInstagramUrl("https://www.instagram.com/p/abc_123/"))
        assertEquals("https://www.instagram.com/reel/abc-123/", validatedInstagramUrl("https://www.instagram.com/reel/abc-123/"))
    }

    @Test fun missingAndInvalidUrlsAreHidden() {
        assertNull(validatedInstagramUrl(null))
        assertNull(validatedInstagramUrl(" "))
        assertNull(validatedInstagramUrl("http://instagram.com/name/"))
        assertNull(validatedInstagramUrl("https://instagram.com.evil.example/name/"))
        assertNull(validatedInstagramUrl("https://www.instagram.com/p/"))
    }

    @Test fun exploreDtoMapsOptionalInstagramUrl() {
        val json = """{"id":1,"title":"Land","instagram_url":"https://instagram.com/name/","land_type":"residential","listing_status":"live","expected_price":100,"price_type":"total_price","area":1,"area_unit":"sqft","location":"Road","city":"City","state":"State","pincode":"12345","boundary_points":[],"images":[],"is_liked":false,"is_offer_locked":false,"created_at":"2026-01-01T00:00:00"}"""
        assertEquals(
            "https://instagram.com/name/",
            Gson().fromJson(json, ExploreLandItemDto::class.java).instagramUrl
        )
    }
}
