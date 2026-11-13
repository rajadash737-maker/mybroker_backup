package com.example.myapplication.ui.feature.buyer.utils

import java.net.URI

private val instagramUsername = Regex("^[A-Za-z0-9._]{1,30}$")
private val shortcode = Regex("^[A-Za-z0-9_-]+$")
private val reserved = setOf("p", "reel", "reels", "stories", "explore", "accounts", "direct")

fun validatedInstagramUrl(raw: String?): String? {
    val value = raw?.trim()?.takeIf { it.isNotEmpty() && !it.any(Char::isWhitespace) && '\\' !in it }
        ?: return null
    val uri = runCatching { URI(value) }.getOrNull() ?: return null
    val host = uri.host?.lowercase() ?: return null
    if (uri.scheme?.lowercase() != "https" ||
        host !in setOf("instagram.com", "www.instagram.com", "m.instagram.com") ||
        uri.userInfo != null || uri.port !in setOf(-1, 443)
    ) return null
    val parts = uri.path.split('/').filter { it.isNotEmpty() }
    val valid = when {
        parts.size == 1 -> instagramUsername.matches(parts[0]) && parts[0].lowercase() !in reserved
        parts.size == 2 && parts[0].lowercase() in setOf("p", "reel", "reels") -> shortcode.matches(parts[1])
        else -> false
    }
    return value.takeIf { valid }
}
