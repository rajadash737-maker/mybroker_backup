package com.example.myapplication.ui.feature.home.profile

import com.google.gson.Gson
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ProfileUpdateRequestBuilderTest {
    @Test
    fun blankOptionalFieldsBecomeNullAndAreOmittedFromJson() {
        val result = buildProfileUpdateRequest(
            fullname = "",
            username = " ",
            email = "",
            mobile = "",
            address = "",
            dateOfBirth = "",
            gender = "Male"
        )

        assertTrue(result.errors.isEmpty())
        val request = requireNotNull(result.request)
        assertNull(request.fullname)
        assertNull(request.username)
        assertNull(request.email)
        assertNull(request.mobile)
        assertNull(request.address)
        assertNull(request.dateOfBirth)
        val json = Gson().toJson(request)
        assertFalse(json.contains("\"fullname\""))
        assertFalse(json.contains("\"date_of_birth\""))
    }

    @Test
    fun validValuesAndSupportedDobFormatArePreserved() {
        val result = buildProfileUpdateRequest(
            fullname = "  Priya Sharma  ",
            username = "Priya_01",
            email = "priya@example.com",
            mobile = "+919876543210",
            address = "  12 Main Road  ",
            dateOfBirth = "09/04/1992",
            gender = "Female"
        )

        assertTrue(result.errors.isEmpty())
        val request = requireNotNull(result.request)
        assertEquals("  Priya Sharma  ", request.fullname)
        assertEquals("Priya_01", request.username)
        assertEquals("priya@example.com", request.email)
        assertEquals("+919876543210", request.mobile)
        assertEquals("  12 Main Road  ", request.address)
        assertEquals("09/04/1992", request.dateOfBirth)
        assertEquals("female", request.gender)
    }

    @Test
    fun invalidInputsReturnFieldSpecificErrorsAndNoRequest() {
        val result = buildProfileUpdateRequest(
            fullname = "A",
            username = "ab",
            email = "not-an-email",
            mobile = "98765 43210",
            address = "",
            dateOfBirth = "31/02/2000",
            gender = "Male"
        )

        assertNull(result.request)
        assertEquals(
            setOf("fullname", "username", "email", "mobile", "date_of_birth"),
            result.errors.keys
        )
        assertTrue(result.errors.getValue("date_of_birth").contains("DD/MM/YYYY"))
        assertTrue(result.errors.getValue("mobile").contains("digits"))
    }

    @Test
    fun backend422ParserMapsFieldWithoutExposingSubmittedInput() {
        val mapped = profileUpdate422Errors(
            """{"detail":[{"loc":["body","date_of_birth"],"msg":"invalid date","input":"private-value"}]}"""
        )

        assertEquals("Enter a valid date in DD/MM/YYYY format.", mapped["date_of_birth"])
        assertFalse(mapped.values.any { it.contains("private-value") })
    }
}
