package com.example.mybroker_admin.feature.superadmin.listings.model

import org.junit.Assert.assertEquals
import org.junit.Test

class SuperAdminListingFiltersTest {
    private val listings = listOf(
        item(1, "PENDING"),
        item(2, "approved"),
        item(3, "FIELD_VERIFIED"),
        item(4, "DRAFT"),
        item(5, "rejected"),
        item(6, "live"),
        item(7, "booked"),
        item(8, "sold"),
        item(9, "needs_correction")
    )

    @Test
    fun statusOptionsPreserveExistingFiltersAndAddDraft() {
        assertEquals(
            listOf("All", "Pending", "Approved", "Field Verified", "Draft", "Live", "Rejected", "Booked", "Sold"),
            SuperAdminListingFilters.statusOptions.map { it.label }
        )
        assertEquals(null, SuperAdminListingFilters.statusOptions.first().value)
        assertEquals("draft", SuperAdminListingFilters.statusOptions.first { it.label == "Draft" }.value)
    }

    @Test
    fun allFilterKeepsEveryListing() {
        assertEquals(listings, SuperAdminListingFilters.filterPage(listings, null))
    }

    @Test
    fun existingStatusFiltersSelectTheirMatchingStatusCaseInsensitively() {
        mapOf(
            "pending" to 1,
            "approved" to 2,
            "field_verified" to 3
        ).forEach { (filter, expectedId) ->
            assertEquals(listOf(expectedId), SuperAdminListingFilters.filterPage(listings, filter).map { it.id })
        }
    }

    @Test
    fun draftFilterIncludesOnlyActualDraftStatus() {
        assertEquals(listOf(4), SuperAdminListingFilters.filterPage(listings, "draft").map { it.id })
        assertEquals(listOf(4), SuperAdminListingFilters.filterPage(listings, "DRAFT").map { it.id })
    }

    private fun item(id: Int, status: String) = SuperAdminListingItem(
        id = id,
        sellerName = "Seller $id",
        sellerMobile = "0000000000",
        status = status
    )
}
