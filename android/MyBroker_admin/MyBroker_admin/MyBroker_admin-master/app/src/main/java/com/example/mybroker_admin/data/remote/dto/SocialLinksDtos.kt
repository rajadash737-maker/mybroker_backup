package com.example.mybroker_admin.data.remote.dto

data class SocialLinksDto(
    val id: Int,
    val whatsapp: String? = null,
    val instagram: String? = null,
    val telegram: String? = null,
    val youtube: String? = null,
    val facebook: String? = null,
    val linkedin: String? = null
)

data class SocialLinksUpdateRequest(
    val whatsapp: String? = null,
    val instagram: String? = null,
    val telegram: String? = null,
    val youtube: String? = null,
    val facebook: String? = null,
    val linkedin: String? = null
)
