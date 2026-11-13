package com.example.mybroker_admin.data.remote.dto

data class BannerDto(
    val id: Int,
    val image_url: String,
    val sort_order: Int,
    val is_active: Boolean
)

data class BannerDeleteResponse(
    val status: String
)
