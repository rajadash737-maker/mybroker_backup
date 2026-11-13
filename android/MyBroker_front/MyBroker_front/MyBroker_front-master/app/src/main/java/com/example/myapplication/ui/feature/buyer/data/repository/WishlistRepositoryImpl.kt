package com.example.myapplication.ui.feature.buyer.data.repository



import com.example.myapplication.ui.feature.buyer.data.remote.LandApi
import com.example.myapplication.ui.feature.buyer.domain.repository.WishlistRepository
import com.example.myapplication.ui.feature.buyer.domain.repository.WishlistUpdateResult

class WishlistRepositoryImpl(
    private val landApi: LandApi
) : WishlistRepository {

    override suspend fun likeLand(landId: Int): WishlistUpdateResult {
        return landApi.likeLand(landId).let { WishlistUpdateResult(it.liked, it.likesCount) }
    }

    override suspend fun unlikeLand(landId: Int): WishlistUpdateResult {
        return landApi.unlikeLand(landId).let { WishlistUpdateResult(it.liked, it.likesCount) }
    }
}
