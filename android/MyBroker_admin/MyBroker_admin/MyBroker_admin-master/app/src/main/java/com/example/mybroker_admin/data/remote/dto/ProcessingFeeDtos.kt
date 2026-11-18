package com.example.mybroker_admin.data.remote.dto

import java.math.BigDecimal

data class ProcessingFeeSettingsDto(
    val id: Int,
    val seller_processing_fee: Double,
    val buyer_processing_fee: Double,
    val site_visit_fee: BigDecimal
)

data class ProcessingFeeUpdateRequest(
    val seller_processing_fee: Double,
    val buyer_processing_fee: Double,
    val site_visit_fee: BigDecimal
)
