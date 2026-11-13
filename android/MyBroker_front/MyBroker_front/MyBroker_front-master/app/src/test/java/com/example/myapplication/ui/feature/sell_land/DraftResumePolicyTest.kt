package com.example.myapplication.ui.feature.sell_land

import com.example.myapplication.ui.feature.sell_land.model.SellLandMediaResponse
import com.example.myapplication.ui.feature.sell_land.model.SellLandResponse
import com.example.myapplication.ui.feature.sell_land.model.SellLandStep
import com.example.myapplication.ui.feature.sell_land.utils.DraftMapper
import com.example.myapplication.ui.feature.sell_land.utils.SellLandDraftLoader
import com.example.myapplication.ui.feature.sell_land.utils.DraftSaveSerialiser
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class DraftResumePolicyTest {
    @Test
    fun onlyGenuineDraftRowsAreCandidates() {
        val candidates = DraftMapper.genuineDrafts(
            listOf(listing(1), listing(2, isDraft = false), listing(3, status = "REJECTED"), listing(4, status = "CORRECTION"))
        )
        assertEquals(listOf(1), candidates.map { it.id })
    }

    @Test
    fun zeroOneAndMultipleDraftsAreDistinguishableAndListingIdsRemainStable() {
        assertTrue(DraftMapper.genuineDrafts(emptyList()).isEmpty())
        assertEquals(21, DraftMapper.genuineDrafts(listOf(listing(21))).single().id)
        assertEquals(listOf(21, 22), DraftMapper.genuineDrafts(listOf(listing(21), listing(22))).map { it.id })
    }

    @Test
    fun savedStepMapsToItsRouteStepAndInvalidValuesFallBackToSeller() {
        assertEquals(SellLandStep.SELLER, DraftMapper.stepFromDraftStep(1))
        assertEquals(SellLandStep.LAND, DraftMapper.stepFromDraftStep(2))
        assertEquals(SellLandStep.MEDIA, DraftMapper.stepFromDraftStep(3))
        assertEquals(SellLandStep.MAP, DraftMapper.stepFromDraftStep(4))
        assertEquals(SellLandStep.PRICING, DraftMapper.stepFromDraftStep(5))
        assertEquals(SellLandStep.REVIEW, DraftMapper.stepFromDraftStep(6))
        assertEquals(SellLandStep.PAYMENT, DraftMapper.stepFromDraftStep(7))
        assertEquals(SellLandStep.SELLER, DraftMapper.stepFromDraftStep(null))
        assertEquals(SellLandStep.SELLER, DraftMapper.stepFromDraftStep(99))
    }

    @Test
    fun loadedDraftRestoresSellerLandBoundaryMediaDocumentsAndPricingWithoutConversion() {
        val response = listing(37).copy(
            ownerName = "Seller",
            ownerMobile = "9876543210",
            title = "Farm",
            area = 12.0,
            areaUnit = "acre",
            city = "Puri",
            state = "Odisha",
            boundaryPoints = "[{\"lat\":20.0,\"lng\":85.0},{\"lat\":20.1,\"lng\":85.1},{\"lat\":20.2,\"lng\":85.2}]",
            priceType = "price_per_unit",
            expectedPrice = 12.5,
            pricingVersion = 1,
            draftStep = 5
        )
        val media = listOf(
            media(1, "photo", null, "photo-url"),
            media(2, "document", "sale_deed", "deed-url"),
            media(3, "document", "latest_tax_receipt", "tax-url")
        )

        val draft = DraftMapper.fromExistingListing(response, media)

        assertEquals("Seller", draft.sellerDetails?.name)
        assertEquals("Farm", draft.landDetails?.title)
        assertEquals("Puri", draft.landDetails?.city)
        assertEquals(3, draft.polygon.size)
        assertEquals(listOf("photo-url"), draft.images)
        assertEquals("deed-url", draft.documents.saleDeed)
        assertEquals("tax-url", draft.documents.dynamicDocs["latest_tax_receipt"])
        assertEquals(12.5, draft.pricing!!.price, 0.0)
        assertTrue(draft.pricing!!.isLegacyPerUnit)
        assertEquals(SellLandStep.PRICING, draft.lastStep)
    }

    @Test
    fun reconciliationFindsOnlyDraftsCreatedSinceNewListingFlowStarted() {
        val discovered = DraftMapper.newlyCreatedDrafts(
            listOf(listing(10), listing(11), listing(12, status = "REJECTED")),
            setOf(10)
        )
        assertEquals(listOf(11), discovered.map { it.id })
    }

    @Test
    fun detailFailureDoesNotProduceDraftOrFetchAndApplyMedia() = runBlocking {
        var mediaRequested = false
        val loader = SellLandDraftLoader(
            getListings = { Result.success(emptyList()) },
            getListingDetails = { Result.failure(IllegalStateException("detail offline")) },
            getListingMedia = {
                mediaRequested = true
                Result.success(emptyList())
            }
        )

        val result = loader.load(37)

        assertTrue(result.isFailure)
        assertFalse(mediaRequested)
    }

    @Test
    fun mediaFailureDoesNotReturnPartiallyHydratedDraft() = runBlocking {
        val loader = SellLandDraftLoader(
            getListings = { Result.success(emptyList()) },
            getListingDetails = { Result.success(listing(it)) },
            getListingMedia = { Result.failure(IllegalStateException("media offline")) }
        )

        val result = loader.load(37)

        assertTrue(result.isFailure)
    }

    @Test
    fun concurrentInitialSavesSerializeAndReuseTheCreatedListingId() = runBlocking {
        val serialiser = DraftSaveSerialiser()
        var currentId: Int? = null
        val requestIds = mutableListOf<Int?>()

        val first = launch {
            serialiser.run {
                requestIds += currentId
                delay(20)
                currentId = 88
            }
        }
        val second = launch {
            serialiser.run {
                requestIds += currentId
                delay(1)
            }
        }
        first.join()
        second.join()

        assertEquals(listOf(null, 88), requestIds)
    }

    private fun listing(id: Int, isDraft: Boolean = true, status: String = "DRAFT") = SellLandResponse(
        id = id, userId = 8, landType = "residential", ownershipType = "single_owner",
        areaUnit = "sqft", priceType = "total_price", negotiable = false,
        availability = "immediate", isDraft = isDraft, draftStep = 2,
        paymentRequiredAmount = 0.0, paymentStatus = "pending", status = status,
        createdAt = "2026-01-01", updatedAt = "2026-01-01"
    )

    private fun media(id: Int, type: String, documentType: String?, url: String) = SellLandMediaResponse(
        id = id, requestId = 37, mediaType = type, documentType = documentType,
        fileUrl = url, fileName = "item", isRequired = false, createdAt = "2026-01-01"
    )
}
