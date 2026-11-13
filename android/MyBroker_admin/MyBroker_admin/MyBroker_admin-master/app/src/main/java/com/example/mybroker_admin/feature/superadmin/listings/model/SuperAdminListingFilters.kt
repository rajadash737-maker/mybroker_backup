package com.example.mybroker_admin.feature.superadmin.listings.model

data class SuperAdminListingStatusOption(
    val label: String,
    val value: String?
)

object SuperAdminListingFilters {
    val statusOptions = listOf(
        SuperAdminListingStatusOption("All", null),
        SuperAdminListingStatusOption("Pending", "pending"),
        SuperAdminListingStatusOption("Approved", "approved"),
        SuperAdminListingStatusOption("Field Verified", "field_verified"),
        SuperAdminListingStatusOption("Draft", "draft"),
        SuperAdminListingStatusOption("Live", "live"),
        SuperAdminListingStatusOption("Rejected", "rejected"),
        SuperAdminListingStatusOption("Booked", "booked"),
        SuperAdminListingStatusOption("Sold", "sold")
    )

    /** Defensive check for each server-filtered page; the API remains responsible for pagination. */
    fun filterPage(
        listings: List<SuperAdminListingItem>,
        statusFilter: String?
    ): List<SuperAdminListingItem> = listings.filter { item ->
        statusFilter == null || item.status.equals(statusFilter, ignoreCase = true)
    }
}
