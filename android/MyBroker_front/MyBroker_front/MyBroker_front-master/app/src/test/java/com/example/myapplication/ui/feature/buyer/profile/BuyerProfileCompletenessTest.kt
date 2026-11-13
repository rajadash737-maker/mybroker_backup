package com.example.myapplication.ui.feature.buyer.profile

import com.example.myapplication.network.UserProfileResponse
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class BuyerProfileCompletenessTest {
    @Test
    fun completeProfileHasNoMissingOfferFields() {
        assertTrue(missingBuyerOfferProfileFields(completeProfile()).isEmpty())
    }

    @Test
    fun incompleteProfileListsOnlyMissingOfferFields() {
        val profile = completeProfile().copy(
            username = " ",
            mobile = null,
            dateOfBirth = ""
        )

        assertEquals(
            listOf("Username", "Mobile Number", "Date of Birth"),
            missingBuyerOfferProfileFields(profile)
        )
    }

    @Test
    fun absentProfileFailsClosedWithEveryRequiredField() {
        assertEquals(
            listOf("Full Name", "Username", "Email", "Mobile Number", "Address", "Date of Birth"),
            missingBuyerOfferProfileFields(null)
        )
    }

    private fun completeProfile() = UserProfileResponse(
        fullname = "Buyer Name",
        username = "buyer.name",
        email = "buyer@example.com",
        mobile = "919876543210",
        address = "Buyer address",
        dateOfBirth = "1990-01-01"
    )
}
