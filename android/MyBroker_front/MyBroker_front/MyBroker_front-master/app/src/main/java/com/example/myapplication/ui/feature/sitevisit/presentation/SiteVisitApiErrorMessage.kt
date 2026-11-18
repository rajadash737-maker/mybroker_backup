package com.example.myapplication.ui.feature.sitevisit.presentation

import com.google.gson.JsonArray
import com.google.gson.JsonElement
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import retrofit2.HttpException

/** Converts FastAPI/Retrofit failures to short, safe copy suitable for the booking form. */
object SiteVisitApiErrorMessage {
    fun refundDetails(error: Throwable): String {
        val status = generateSequence(error) { it.cause }
            .filterIsInstance<HttpException>()
            .firstOrNull()?.code()
        return if (status == 503) {
            "Refund details could not be saved securely. Your booking remains cancelled and refund details are still required; try again later or contact support."
        } else {
            from(error)
        }
    }

    fun from(error: Throwable): String {
        val httpError = generateSequence(error) { it.cause }
            .filterIsInstance<HttpException>()
            .firstOrNull()
            ?: return "We couldn't submit your Site Visit request. Check your connection and try again."

        // Server failures can contain infrastructure details even when the body looks like text.
        if (httpError.code() == 500) return statusFallback(500)

        val backendMessage = runCatching {
            httpError.response()?.errorBody()?.string()?.let(::parseDetail)
        }.getOrNull()
        return backendMessage?.let(::friendlyBackendMessage) ?: statusFallback(httpError.code())
    }

    internal fun parseDetail(body: String): String? = runCatching {
        val root = JsonParser.parseString(body)
        if (!root.isJsonObject) return@runCatching null
        val detail = root.asJsonObject.get("detail") ?: return@runCatching null
        when {
            detail.isJsonPrimitive && detail.asJsonPrimitive.isString -> detail.asString
            detail.isJsonArray -> parseValidationDetails(detail.asJsonArray)
            else -> null
        }
    }.getOrNull()?.takeIf(String::isNotBlank)

    private fun parseValidationDetails(details: JsonArray): String? {
        val messages = details.mapNotNull { item ->
            if (!item.isJsonObject) return@mapNotNull null
            val obj = item.asJsonObject
            val message = obj.getStringOrNull("msg") ?: return@mapNotNull null
            val location = obj.get("loc")?.let(::locationLabel)
            val safeMessage = friendlyBackendMessage(message) ?: return@mapNotNull null
            if (location != null && !isGenericFriendly(safeMessage)) "$location: $safeMessage" else safeMessage
        }.distinct()
        return messages.takeIf { it.isNotEmpty() }?.take(3)?.joinToString(" ")
    }

    private fun locationLabel(location: JsonElement): String? {
        if (!location.isJsonArray) return null
        val field = location.asJsonArray.lastOrNull()?.takeIf { it.isJsonPrimitive }?.asString ?: return null
        return when (field.lowercase()) {
            "preferred_visit_date" -> "Preferred date"
            "preferred_visit_time" -> "Preferred time"
            "visitor_count" -> "Number of visitors"
            "pickup_address" -> "Pickup address"
            "listing_id" -> "Property"
            "submission_key" -> "Request"
            else -> null
        }
    }

    private fun friendlyBackendMessage(message: String): String? {
        val normalized = message.trim().lowercase()
        return when {
            "refund detail encryption is not configured" in normalized || "refund details could not be saved securely" in normalized ->
                "Refund details could not be saved securely. Your booking remains cancelled and refund details are still required; try again later or contact support."
            "registered mobile" in normalized -> "Please register your mobile number before booking a Site Visit."
            "preferred_visit_date cannot be in the past" in normalized || "preferred visit date cannot be in the past" in normalized ->
                "Preferred visit date cannot be in the past."
            "active site visit request already exists" in normalized || "active site visit booking" in normalized ->
                "You already have an active Site Visit booking for this property."
            "submission key was already used for a different" in normalized || "request key" in normalized && "different" in normalized ->
                "This request changed after it was first submitted. Refresh your bookings before trying again; start a new request only after confirming no booking was created."
            else -> message.takeIf(::isSafeBackendText)
        }
    }

    private fun isSafeBackendText(message: String): Boolean {
        val value = message.trim()
        if (value.isEmpty() || value.length > 180 || value.any { it.isISOControl() }) return false
        val lower = value.lowercase()
        val sensitiveOrInternal = listOf(
            "traceback", "stack trace", "exception", "select ", "insert ", "update ", "delete ",
            "drop ", "alter ", "sql", "database", "password", "credential", "authorization",
            "bearer ", "token", "secret", "signature", " at app.", "file \"", "internal server"
        )
        return sensitiveOrInternal.none(lower::contains) && value.none { it == '<' || it == '>' || it == '{' || it == '}' }
    }

    private fun isGenericFriendly(message: String): Boolean = message in setOf(
        "Please register your mobile number before booking a Site Visit.",
        "Preferred visit date cannot be in the past.",
        "You already have an active Site Visit booking for this property."
    ) || message.startsWith("This request changed after it was first submitted.")

    private fun statusFallback(status: Int): String = when (status) {
        400 -> "Some booking details are invalid. Review them and try again."
        401 -> "Please sign in again before booking a Site Visit."
        403 -> "You aren't allowed to submit this Site Visit request."
        404 -> "This property could not be found. Refresh the listing and try again."
        409 -> "A booking conflict occurred. Refresh your Site Visit bookings before trying again."
        422 -> "Some booking details need attention. Review the date, time, and required fields."
        500 -> "The Site Visit service is temporarily unavailable. Your request key is unchanged; check your bookings before retrying."
        503 -> "The Site Visit service is temporarily unavailable. Your booking is unchanged; check its status and retry later."
        else -> "We couldn't submit your Site Visit request. Check your bookings before retrying."
    }

    private fun JsonObject.getStringOrNull(name: String): String? =
        get(name)?.takeIf { it.isJsonPrimitive && it.asJsonPrimitive.isString }?.asString
}
