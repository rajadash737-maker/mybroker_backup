package com.example.mybroker_admin.data.remote

import com.example.mybroker_admin.core.session.SessionManager
import com.example.mybroker_admin.data.remote.api.AuthApi
import com.example.mybroker_admin.data.remote.dto.RefreshRequestDto
import kotlinx.coroutines.runBlocking
import okhttp3.Authenticator
import okhttp3.Request
import okhttp3.Response
import okhttp3.Route

class TokenAuthenticator(
    private val sessionManager: SessionManager,
    private val refreshApi: AuthApi
) : Authenticator {
    override fun authenticate(route: Route?, response: Response): Request? {
        if (responseCount(response) >= 2) return null

        val path = response.request.url.encodedPath
        if (path.contains("/auth/refresh") || path.contains("/auth/login")) return null

        val refreshToken = sessionManager.refreshToken ?: return null

        val newAccessToken = runBlocking {
            try {
                val refreshResponse = refreshApi.refresh(RefreshRequestDto(refreshToken))
                val tokens = refreshResponse.tokens ?: return@runBlocking null

                sessionManager.saveLogin(
                    access = tokens.access_token,
                    refresh = tokens.refresh_token,
                    role = refreshResponse.user?.role ?: sessionManager.currentUserRole,
                    dashboard = refreshResponse.dashboard_key ?: sessionManager.dashboardKey,
                    fullName = refreshResponse.user?.fullname ?: sessionManager.currentUserName,
                    email = refreshResponse.user?.email ?: sessionManager.currentUserEmail
                )
                ApiClient.setAccessToken(tokens.access_token)
                tokens.access_token
            } catch (_: Exception) {
                sessionManager.clear()
                null
            }
        } ?: return null

        return response.request.newBuilder()
            .header("Authorization", "Bearer $newAccessToken")
            .build()
    }

    private fun responseCount(response: Response): Int {
        var count = 1
        var prior = response.priorResponse
        while (prior != null) {
            count++
            prior = prior.priorResponse
        }
        return count
    }
}
