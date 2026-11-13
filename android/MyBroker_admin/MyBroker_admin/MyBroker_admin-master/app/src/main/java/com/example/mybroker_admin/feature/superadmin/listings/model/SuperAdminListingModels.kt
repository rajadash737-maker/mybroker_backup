package com.example.mybroker_admin.feature.superadmin.listings.model

data class SuperAdminListingItem(
    val id: Int,
    val sellerName: String,
    val sellerMobile: String,
    val status: String
)

data class SuperAdminListingsState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val listings: List<SuperAdminListingItem> = emptyList(),
    val searchQuery: String = "",
    val statusFilter: String? = null,
    val canLoadMore: Boolean = true,
    val isLoadingMore: Boolean = false
)

data class SuperAdminListingDetailState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val instagramInput: String = "",
    val instagramSaving: Boolean = false,
    val instagramMessage: String? = null,
    val instagramError: String? = null
)
