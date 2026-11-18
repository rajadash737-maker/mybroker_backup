package com.example.myapplication.ui.feature.buyer.data.remote.dto

data class IncomingOfferCountDto(
    val seller_pending: Int,
    val buyer_countered: Int,
    val total: Int
)
