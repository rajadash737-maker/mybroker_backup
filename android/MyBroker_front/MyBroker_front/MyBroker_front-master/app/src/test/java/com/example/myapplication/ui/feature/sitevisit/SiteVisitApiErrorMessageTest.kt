package com.example.myapplication.ui.feature.sitevisit

import com.example.myapplication.ui.feature.sitevisit.presentation.SiteVisitApiErrorMessage
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test
import retrofit2.HttpException
import retrofit2.Response

class SiteVisitApiErrorMessageTest {
    @Test fun parsesStringDetailAndMapsMissingMobileToFriendlyCopy() {
        val message = error(
            422,
            """{"detail":"A registered mobile number is required to request a Site Visit"}"""
        )
        assertEquals("Please register your mobile number before booking a Site Visit.", message)
    }

    @Test fun parsesFastApiValidationListAndAddsFriendlyFieldLabel() {
        val message = error(
            422,
            """{"detail":[{"loc":["body","preferred_visit_date"],"msg":"Preferred visit date cannot be in the past","type":"value_error"}]}"""
        )
        assertEquals("Preferred visit date cannot be in the past.", message)
    }

    @Test fun mapsActiveBookingAndChangedSubmissionKeyConflictsSafely() {
        assertEquals(
            "You already have an active Site Visit booking for this property.",
            error(409, """{"detail":"An active Site Visit request already exists for this listing"}""")
        )
        val changedKey = error(
            409,
            """{"detail":"Submission key was already used for a different Site Visit request"}"""
        )
        assertTrue(changedKey.contains("Refresh your bookings"))
        assertTrue(changedKey.contains("only after confirming no booking was created"))
    }

    @Test fun hidesInternalServerDetailsAndUsesSafeFallback() {
        val message = error(500, """{"detail":"DatabaseError: SELECT * FROM users WHERE token='secret'"}""")
        assertEquals(
            "The Site Visit service is temporarily unavailable. Your request key is unchanged; check your bookings before retrying.",
            message
        )
        assertFalse(message.contains("SELECT", ignoreCase = true))
        assertFalse(message.contains("secret", ignoreCase = true))
    }

    @Test fun explainsRefundEncryptionUnavailableWithoutExposingConfiguration() {
        val response = Response.error<Any>(
            503,
            """{"detail":"Refund detail encryption is not configured"}"""
                .toResponseBody("application/json".toMediaType())
        )
        val message = SiteVisitApiErrorMessage.refundDetails(HttpException(response))
        assertEquals(
            "Refund details could not be saved securely. Your booking remains cancelled and refund details are still required; try again later or contact support.",
            message
        )
        assertFalse(message.contains("key", ignoreCase = true))
        assertFalse(message.contains("UPI ID", ignoreCase = true))
    }

    @Test fun usesStatusSpecificFriendlyFallbackForStringlessFastApiErrors() {
        assertEquals(
            "Please sign in again before booking a Site Visit.",
            error(401, """{"detail":null}""")
        )
        assertEquals(
            "This property could not be found. Refresh the listing and try again.",
            error(404, """{"detail":null}""")
        )
        assertEquals(
            "You aren't allowed to submit this Site Visit request.",
            error(403, """{"detail":null}""")
        )
        assertEquals(
            "Some booking details need attention. Review the date, time, and required fields.",
            error(422, """{"detail":null}""")
        )
        assertEquals(
            "Some booking details are invalid. Review them and try again.",
            error(400, "not json")
        )
    }

    private fun error(status: Int, body: String): String {
        val response = Response.error<Any>(
            status,
            body.toResponseBody("application/json".toMediaType())
        )
        return SiteVisitApiErrorMessage.from(HttpException(response))
    }

    private fun assertTrue(value: Boolean) = org.junit.Assert.assertTrue(value)
}
