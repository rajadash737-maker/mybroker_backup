package com.example.myapplication.ui.feature.sell_land

import com.example.myapplication.ui.feature.sell_land.model.PricingDetails
import com.example.myapplication.ui.feature.sell_land.model.SellLandDraftRequest
import com.example.myapplication.ui.feature.sell_land.model.SellLandResponse
import com.example.myapplication.ui.feature.sell_land.model.sellerPricingRequestFields
import com.example.myapplication.ui.feature.sell_land.utils.DraftMapper
import com.google.gson.Gson
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SellerPricingContractTest {
    @Test
    fun v2PricingRequestSendsEnteredTotalUnchangedAndOmitsUnitPrice() {
        val fields = sellerPricingRequestFields(
            PricingDetails(
                priceType = "total_price",
                price = 12345.67,
                negotiable = false,
                availability = "immediate",
                pricingVersion = 2
            )
        )
        val json = Gson().toJson(
            SellLandDraftRequest(
                pricingVersion = fields.pricingVersion,
                priceType = fields.priceType,
                expectedPrice = fields.expectedPrice
            )
        )

        assertTrue(json.contains("\"pricing_version\":2"))
        assertTrue(json.contains("\"price_type\":\"total_price\""))
        assertTrue(json.contains("\"expected_price\":12345.67"))
        assertFalse(json.contains("entered_unit_price"))
    }

    @Test
    fun legacyPerUnitDraftKeepsStoredRateAndOmitsPricingFieldsFromSavePayload() {
        val draft = DraftMapper.fromExistingListing(
            listing(priceType = "price_per_unit", expectedPrice = 12.5, pricingVersion = 1),
            emptyList()
        )
        val pricing = draft.pricing!!
        val fields = sellerPricingRequestFields(pricing)
        val json = Gson().toJson(
            SellLandDraftRequest(
                pricingVersion = fields.pricingVersion,
                priceType = fields.priceType,
                expectedPrice = fields.expectedPrice
            )
        )

        assertTrue(pricing.isLegacyPerUnit)
        assertEquals(12.5, pricing.price, 0.0)
        assertNull(fields.pricingVersion)
        assertNull(fields.priceType)
        assertNull(fields.expectedPrice)
        assertFalse(json.contains("pricing_version"))
        assertFalse(json.contains("price_type"))
        assertFalse(json.contains("expected_price"))
    }

    @Test
    fun legacyTotalPriceDraftKeepsItsVersionAndAmount() {
        val draft = DraftMapper.fromExistingListing(
            listing(priceType = "total_price", expectedPrice = 98765.25, pricingVersion = null),
            emptyList()
        )
        val fields = sellerPricingRequestFields(draft.pricing)

        assertEquals(1, draft.pricing!!.pricingVersion)
        assertEquals(98765.25, fields.expectedPrice!!, 0.0)
        assertEquals(1, fields.pricingVersion)
        assertEquals("total_price", fields.priceType)
    }

    private fun listing(
        priceType: String,
        expectedPrice: Double,
        pricingVersion: Int?
    ) = SellLandResponse(
        id = 1,
        userId = 2,
        landType = "residential",
        ownershipType = "single_owner",
        areaUnit = "sqft",
        pricingVersion = pricingVersion,
        priceType = priceType,
        expectedPrice = expectedPrice,
        negotiable = false,
        availability = "immediate",
        isDraft = true,
        draftStep = 5,
        paymentRequiredAmount = 999.0,
        paymentStatus = "initiated",
        status = "draft",
        createdAt = "2026-01-01T00:00:00",
        updatedAt = "2026-01-01T00:00:00"
    )
}
