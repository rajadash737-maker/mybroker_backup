package com.example.myapplication.ui.feature.sell_land.utils

import com.example.myapplication.ui.feature.sell_land.model.SellLandMediaResponse
import com.example.myapplication.ui.feature.sell_land.model.SellLandResponse
import com.example.myapplication.ui.feature.sell_land.model.SellLandDraft

data class LoadedSellLandDraft(
    val listing: SellLandResponse,
    val media: List<SellLandMediaResponse>,
    val draft: SellLandDraft
)

/** Loads a seller draft as an all-or-nothing detail + media snapshot. */
class SellLandDraftLoader(
    private val getListings: suspend () -> Result<List<SellLandResponse>>,
    private val getListingDetails: suspend (Int) -> Result<SellLandResponse>,
    private val getListingMedia: suspend (Int) -> Result<List<SellLandMediaResponse>>
) {
    suspend fun getDraftCandidates(): Result<List<SellLandResponse>> =
        getListings().map(DraftMapper::genuineDrafts)

    suspend fun load(requestId: Int): Result<LoadedSellLandDraft> {
        val detail = getListingDetails(requestId)
        if (detail.isFailure) return Result.failure(detail.exceptionOrNull()!!)

        val media = getListingMedia(requestId)
        if (media.isFailure) return Result.failure(media.exceptionOrNull()!!)

        val listing = detail.getOrThrow()
        val mediaItems = media.getOrThrow()
        return Result.success(
            LoadedSellLandDraft(
                listing = listing,
                media = mediaItems,
                draft = DraftMapper.fromExistingListing(listing, mediaItems)
            )
        )
    }
}
