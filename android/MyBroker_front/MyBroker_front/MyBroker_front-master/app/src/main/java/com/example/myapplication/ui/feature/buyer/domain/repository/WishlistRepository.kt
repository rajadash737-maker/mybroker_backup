package com.example.myapplication.ui.feature.buyer.domain.repository



data class WishlistUpdateResult(
    val liked: Boolean,
    val likesCount: Int?
)

interface WishlistRepository {

    suspend fun likeLand(landId: Int): WishlistUpdateResult

    suspend fun unlikeLand(landId: Int): WishlistUpdateResult
}
