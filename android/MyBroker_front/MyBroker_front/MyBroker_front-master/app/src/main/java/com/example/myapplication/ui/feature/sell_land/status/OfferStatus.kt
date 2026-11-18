package com.example.myapplication.ui.feature.sell_land.status

enum class OfferStatus {
    PENDING,
    ACCEPTED,
    REJECTED,
    COUNTERED,
    EXPIRED
}

fun offerStatusFromApi(raw: String): OfferStatus = when (raw.trim().uppercase()) {
    "PENDING" -> OfferStatus.PENDING
    "ACCEPTED" -> OfferStatus.ACCEPTED
    "REJECTED" -> OfferStatus.REJECTED
    "COUNTERED" -> OfferStatus.COUNTERED
    "EXPIRED" -> OfferStatus.EXPIRED
    else -> OfferStatus.PENDING
}
