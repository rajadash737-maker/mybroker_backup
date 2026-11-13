package com.example.myapplication.ui.feature.home.profile

import com.example.myapplication.network.UpdateProfileRequest
import com.google.gson.JsonParser
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.time.format.ResolverStyle
import java.util.Locale

data class ProfileUpdateBuildResult(
    val request: UpdateProfileRequest?,
    val errors: Map<String, String>
)

fun buildProfileUpdateRequest(
    fullname: String,
    username: String,
    email: String,
    mobile: String,
    address: String,
    dateOfBirth: String,
    gender: String
): ProfileUpdateBuildResult {
    val errors = linkedMapOf<String, String>()

    if (fullname.isNotBlank() &&
        (fullname.length !in 2..100 || fullname.trim().length < 2 || fullname.trim().length > 100)
    ) {
        errors["fullname"] = "Full name must be between 2 and 100 characters."
    }

    val normalizedUsername = username.trim()
    if (username.isNotBlank() &&
        (username.length !in 3..50 || normalizedUsername.length !in 3..50)
    ) {
        errors["username"] = "Username must be between 3 and 50 characters."
    }

    if (email.isNotBlank() && !EMAIL_PATTERN.matches(email)) {
        errors["email"] = "Enter a valid email address."
    }

    if (mobile.isNotBlank() && !MOBILE_PATTERN.matches(mobile)) {
        errors["mobile"] = "Use 10 to 15 digits, with an optional leading +."
    }

    if (address.isNotBlank() && address.length > 255) {
        errors["address"] = "Address must be 255 characters or fewer."
    }

    if (dateOfBirth.isNotBlank() && !isSupportedDateOfBirth(dateOfBirth)) {
        errors["date_of_birth"] = "Enter a valid date in DD/MM/YYYY format."
    }

    if (errors.isNotEmpty()) return ProfileUpdateBuildResult(request = null, errors = errors)

    return ProfileUpdateBuildResult(
        request = UpdateProfileRequest(
            fullname = fullname.takeUnless { it.isBlank() },
            username = username.takeUnless { it.isBlank() },
            email = email.takeUnless { it.isBlank() },
            mobile = mobile.takeUnless { it.isBlank() },
            address = address.takeUnless { it.isBlank() },
            dateOfBirth = dateOfBirth.takeUnless { it.isBlank() },
            gender = gender.lowercase(Locale.ROOT)
        ),
        errors = emptyMap()
    )
}

private fun isSupportedDateOfBirth(value: String): Boolean = try {
    LocalDate.parse(value, DOB_FORMATTER)
    true
} catch (_: Exception) {
    false
}

private val DOB_FORMATTER = DateTimeFormatter
    .ofPattern("dd/MM/uuuu", Locale.ROOT)
    .withResolverStyle(ResolverStyle.STRICT)

private val EMAIL_PATTERN = Regex(
    "^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\\.)+[A-Za-z]{2,63}$"
)
private val MOBILE_PATTERN = Regex("^(?:\\+[0-9]{10,14}|[0-9]{10,15})$")

/** Maps FastAPI's 422 locations to safe, field-specific text without displaying submitted values. */
fun profileUpdate422Errors(errorBody: String?): Map<String, String> {
    val formError = mapOf("_form" to "The server rejected the profile update. Check the fields and try again.")
    if (errorBody.isNullOrBlank()) return formError

    return runCatching {
        val root = JsonParser.parseString(errorBody).asJsonObject
        val details = root.get("detail")
        if (details == null || !details.isJsonArray) return@runCatching formError

        buildMap {
            details.asJsonArray.forEach { detail ->
                if (!detail.isJsonObject) return@forEach
                val item = detail.asJsonObject
                val location = item.getAsJsonArray("loc") ?: return@forEach
                val field = location.lastOrNull()?.asString ?: return@forEach
                val message = item.get("msg")?.asString.orEmpty()
                val fieldError = when (field) {
                    "fullname" -> "Full name must be between 2 and 100 characters."
                    "username" -> "Username must be between 3 and 50 characters."
                    "email" -> "Enter a valid email address."
                    "mobile" -> if (message.contains("numeric", ignoreCase = true)) {
                        "Use digits only, with an optional leading +."
                    } else {
                        "Use 10 to 15 digits, with an optional leading +."
                    }
                    "address" -> "Address must be 255 characters or fewer."
                    "date_of_birth" -> "Enter a valid date in DD/MM/YYYY format."
                    "gender" -> "Choose Male, Female, or Other."
                    else -> null
                }
                if (fieldError == null) {
                    put("_form", "The server rejected the profile update. Check the fields and try again.")
                } else {
                    put(field, fieldError)
                }
            }
        }.ifEmpty { formError }
    }.getOrDefault(formError)
}
