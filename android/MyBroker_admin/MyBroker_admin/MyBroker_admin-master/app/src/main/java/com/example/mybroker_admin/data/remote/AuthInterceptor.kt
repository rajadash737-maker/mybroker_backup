package com.example.mybroker_admin.data.remote

import okhttp3.Interceptor
import okhttp3.Response

class AuthInterceptor(
    private val accessTokenProvider: () -> String?
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val original = chain.request()
        val path = original.url.encodedPath

        val isAuthEndpoint = path.contains("/auth/login") || path.contains("/auth/refresh")
        if (isAuthEndpoint) return chain.proceed(original)

        val token = accessTokenProvider()?.takeIf { it.isNotBlank() }
        val request = if (token != null) {
            original.newBuilder()
                .header("Authorization", "Bearer $token")
                .build()
        } else original

        return chain.proceed(request)
    }
}
