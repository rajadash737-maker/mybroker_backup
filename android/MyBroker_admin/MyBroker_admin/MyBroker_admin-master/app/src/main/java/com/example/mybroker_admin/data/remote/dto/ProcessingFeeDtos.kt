package com.example.mybroker_admin.data.remote.dto

data class ProcessingFeeSettingsDto(
    val id: Int,
    val seller_processing_fee: Double,
    val buyer_processing_fee: Double
)

data class ProcessingFeeUpdateRequest(
    val seller_processing_fee: Double,
    val buyer_processing_fee: Double
)
