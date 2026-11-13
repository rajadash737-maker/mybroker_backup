package com.example.myapplication.network

import java.io.IOException

class AuthRepository(
    private val api: ApiService,
    private val session: SessionManager
) {
    suspend fun loginWithGoogle(idToken: String): Result<Unit> = try {
        val response = api.googleLogin(GoogleAuthRequest(id_token = idToken))
        if (!response.isSuccessful) {
            val detail = response.errorBody()?.use { errorBody ->
                runCatching {
                    org.json.JSONObject(errorBody.string()).optString("detail").takeIf { it.isNotBlank() }
                }.getOrNull()
            }
            val message = when (response.code()) {
                401 -> "Google sign-in token was rejected. Please try again."
                403 -> detail ?: "This account is deactivated."
                503 -> "Google sign-in is not configured on the server."
                else -> detail ?: "Google sign-in failed (HTTP ${response.code()})."
            }
            error(message)
        }

        val body = response.body() ?: error("Google sign-in returned an empty response.")
        val tokens = body.tokens ?: error(body.status.ifBlank { "Google sign-in did not return app tokens." })
        session.saveTokens(tokens.access_token, tokens.refresh_token)
        Result.success(Unit)
    } catch (_: IOException) {
        Result.failure(IllegalStateException("Network error. Check your connection and try again."))
    } catch (error: Exception) {
        Result.failure(error)
    }

    suspend fun login(identifier: String, password: String): Result<Unit> = runCatching {
        val res = api.login(LoginRequest(identifier = identifier, password = password))
        if (!res.isSuccessful) error("Login failed: ${res.code()}")

        val body = res.body() ?: error("Empty response")
        val tokens = body.tokens ?: error(body.status)

        session.saveTokens(tokens.access_token, tokens.refresh_token)
    }

    suspend fun logout() {
        val refresh = session.getRefreshToken()
        if (!refresh.isNullOrBlank()) {
            runCatching { api.logout(LogoutRequest(refresh_token = refresh)) }
        }
        session.clearSession()
    }

    fun isLoggedIn(): Boolean = session.isLoggedIn()
}
