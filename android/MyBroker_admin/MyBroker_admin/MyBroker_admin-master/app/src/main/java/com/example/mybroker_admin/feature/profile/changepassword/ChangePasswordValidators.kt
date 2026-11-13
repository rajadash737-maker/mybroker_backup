package com.example.mybroker_admin.feature.profile.changepassword

import android.util.Patterns

fun validateEmail(email: String): String? {
    val value = email.trim()
    return when {
        value.isEmpty() -> "Email is required"
        !Patterns.EMAIL_ADDRESS.matcher(value).matches() -> "Enter a valid email address"
        else -> null
    }
}

fun validatePassword(password: String): String? {
    val value = password.trim()
    return when {
        value.isEmpty() -> "New password is required"
        value.length < 8 -> "Password must be at least 8 characters"
        value.none { it.isUpperCase() } -> "Password must include at least one uppercase letter"
        value.none { it.isLowerCase() } -> "Password must include at least one lowercase letter"
        value.none { it.isDigit() } -> "Password must include at least one number"
        else -> null
    }
}

fun matchPassword(password: String, confirmPassword: String): String? {
    return when {
        confirmPassword.isBlank() -> "Confirm your new password"
        password != confirmPassword -> "Passwords do not match"
        else -> null
    }
}

internal fun validateRequired(value: String, fieldName: String): String? {
    return if (value.trim().isBlank()) "$fieldName is required" else null
}

internal fun normalizeChangePasswordRole(rawRole: String?): String {
    return when (rawRole?.trim()?.lowercase()) {
        "admin", "super_admin", "super admin" -> "admin"
        "field_officer", "field officer" -> "field_officer"
        "accountant", "accounting" -> "accountant"
        else -> rawRole?.trim()?.lowercase().orEmpty()
    }
}

internal fun formatRoleLabel(rawRole: String?): String {
    return when (normalizeChangePasswordRole(rawRole)) {
        "admin" -> "Admin"
        "field_officer" -> "Field Officer"
        "accountant" -> "Accountant"
        else -> rawRole?.replace("_", " ")
            ?.split(" ")
            ?.joinToString(" ") { token -> token.replaceFirstChar { it.uppercase() } }
            .orEmpty()
    }
}
