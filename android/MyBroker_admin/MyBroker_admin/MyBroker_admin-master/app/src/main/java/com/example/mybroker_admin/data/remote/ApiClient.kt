package com.example.mybroker_admin.data.remote

import android.net.Uri
import com.example.mybroker_admin.core.config.AppEnv
import com.example.mybroker_admin.data.remote.api.AccountingListingApi
import com.example.mybroker_admin.data.remote.api.AdminListingApi
import com.example.mybroker_admin.data.remote.api.AuthApi
import com.example.mybroker_admin.data.remote.api.FieldOfficerApi
import com.example.mybroker_admin.data.remote.api.NotificationApi
import com.example.mybroker_admin.data.remote.api.ProfileApi
import com.example.mybroker_admin.data.remote.api.SettingsApi
import com.example.mybroker_admin.data.remote.api.StaffAnalyticsApi
import com.example.mybroker_admin.data.remote.api.StaffApi
import okhttp3.OkHttpClient
import okhttp3.ResponseBody
import retrofit2.Retrofit
import retrofit2.Response
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.Streaming
import retrofit2.http.Url
import java.io.IOException

object ApiClient {
    private const val BASE_URL = AppEnv.BASE_URL
    private val baseUri: Uri by lazy { Uri.parse(BASE_URL) }

    @Volatile
    private var accessToken: String? = null

    fun setAccessToken(token: String?) {
        accessToken = token
    }

    fun absoluteUrl(path: String?): String? {
        if (path.isNullOrBlank()) return null

        val cleaned = path.trim().replace("\\", "/")
        val lower = cleaned.lowercase()

        if (lower.startsWith("content://") || lower.startsWith("file://")) return cleaned

        if (lower.startsWith("http://") || lower.startsWith("https://")) {
            val parsed = Uri.parse(cleaned)
            val host = parsed.host?.lowercase().orEmpty()
            val baseHost = baseUri.host?.lowercase().orEmpty()

            val isLocalLike =
                host == "localhost" ||
                        host == "127.0.0.1" ||
                        host == "0.0.0.0" ||
                        host.startsWith("10.") ||
                        host.startsWith("192.168.") ||
                        host.startsWith("172.16.") ||
                        host.startsWith("172.17.") ||
                        host.startsWith("172.18.") ||
                        host.startsWith("172.19.") ||
                        host.startsWith("172.2") ||
                        host.startsWith("172.30.") ||
                        host.startsWith("172.31.")

            if (isLocalLike && host != baseHost) {
                return parsed.buildUpon()
                    .scheme(baseUri.scheme)
                    .encodedAuthority(baseUri.encodedAuthority)
                    .build()
                    .toString()
            }

            return cleaned
        }

        val normalizedPath = if (cleaned.startsWith("/")) cleaned else "/$cleaned"
        return BASE_URL.removeSuffix("/") + normalizedPath
    }

    private val refreshRetrofit: Retrofit by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(OkHttpClient.Builder().build())
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    private val refreshApi: AuthApi by lazy { refreshRetrofit.create(AuthApi::class.java) }

    private val okHttpClient: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .addInterceptor(AuthInterceptor { accessToken })
            .authenticator(TokenAuthenticator(com.example.mybroker_admin.core.session.SessionManager, refreshApi))
            .build()
    }

    val authenticatedMediaOkHttpClient: OkHttpClient by lazy {
        okHttpClient.newBuilder()
            .followRedirects(false)
            .followSslRedirects(false)
            .addInterceptor { chain ->
                val request = chain.request()
                if (!isTrustedApiUrl(request.url.toString())) {
                    throw IOException("Media URL is outside the configured API origin")
                }
                chain.proceed(request)
            }
            .build()
    }

    private val retrofit: Retrofit by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    private val privateMediaApi: PrivateMediaApi by lazy { retrofit.create(PrivateMediaApi::class.java) }

    suspend fun downloadPrivatePdf(pathOrUrl: String): Response<ResponseBody> {
        val url = absoluteUrl(pathOrUrl)
            ?: throw IOException("Document URL is missing")
        val uri = Uri.parse(url)
        val basePort = baseUri.port.takeIf { it != -1 }
            ?: if (baseUri.scheme.equals("https", ignoreCase = true)) 443 else 80
        val requestPort = uri.port.takeIf { it != -1 }
            ?: if (uri.scheme.equals("https", ignoreCase = true)) 443 else 80
        if (!uri.scheme.equals(baseUri.scheme, ignoreCase = true) ||
            !uri.host.equals(baseUri.host, ignoreCase = true) || requestPort != basePort
        ) {
            throw IOException("Document URL is outside the configured API origin")
        }
        return privateMediaApi.downloadPdf(url)
    }

    fun isTrustedApiUrl(url: String): Boolean {
        val uri = Uri.parse(url)
        val basePort = baseUri.port.takeIf { it != -1 }
            ?: if (baseUri.scheme.equals("https", ignoreCase = true)) 443 else 80
        val requestPort = uri.port.takeIf { it != -1 }
            ?: if (uri.scheme.equals("https", ignoreCase = true)) 443 else 80
        return uri.scheme.equals(baseUri.scheme, ignoreCase = true) &&
                uri.host.equals(baseUri.host, ignoreCase = true) &&
                requestPort == basePort
    }

    val authApi: AuthApi by lazy { retrofit.create(AuthApi::class.java) }
    val staffApi: StaffApi by lazy { retrofit.create(StaffApi::class.java) }
    val staffAnalyticsApi: StaffAnalyticsApi by lazy { retrofit.create(StaffAnalyticsApi::class.java) }
    val adminListingApi: AdminListingApi by lazy { retrofit.create(AdminListingApi::class.java) }
    val fieldOfficerApi: FieldOfficerApi by lazy { retrofit.create(FieldOfficerApi::class.java) }
    val profileApi: ProfileApi by lazy { retrofit.create(ProfileApi::class.java) }
    val accountingListingApi: AccountingListingApi by lazy { retrofit.create(AccountingListingApi::class.java) }
    val settingsApi: SettingsApi by lazy { retrofit.create(SettingsApi::class.java) }
    val notificationApi: NotificationApi by lazy { retrofit.create(NotificationApi::class.java) }
}

private interface PrivateMediaApi {
    @Streaming
    @GET
    suspend fun downloadPdf(@Url url: String): Response<ResponseBody>
}
