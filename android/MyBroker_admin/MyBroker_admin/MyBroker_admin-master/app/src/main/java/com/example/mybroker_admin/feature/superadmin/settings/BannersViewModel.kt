

package com.example.mybroker_admin.feature.superadmin.settings

import android.content.ContentResolver
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.repository.SettingsRepository
import com.example.mybroker_admin.data.repository.SettingsRepositoryImpl
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import org.json.JSONObject
import retrofit2.HttpException
import java.io.File

private data class BannerImageFormat(val mimeType: String, val extension: String)

data class BannerUiModel(
    val id: Int,
    val imageUrl: String,
    val sortOrder: Int
)

data class BannerUiState(
    val items: List<BannerUiModel> = emptyList(),
    val isLoading: Boolean = false,
    val isUploading: Boolean = false,
    val message: String? = null
)

class BannersViewModel(
    private val repository: SettingsRepository = SettingsRepositoryImpl(ApiClient.settingsApi)
) : ViewModel() {

    private val _uiState = MutableStateFlow(BannerUiState())
    val uiState: StateFlow<BannerUiState> = _uiState.asStateFlow()

    fun loadBanners() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, message = null)

            runCatching { repository.getBanners() }
                .onSuccess { list ->
                    val mapped = list
                        .filter { it.is_active }
                        .sortedBy { it.sort_order }
                        .map {
                            BannerUiModel(
                                id = it.id,
                                imageUrl = ApiClient.absoluteUrl(it.image_url).orEmpty(),
                                sortOrder = it.sort_order
                            )
                        }
                    _uiState.value = _uiState.value.copy(isLoading = false, items = mapped)
                }
                .onFailure { e ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        message = parseApiError(e, "Failed to load banners")
                    )
                }
        }
    }

    fun uploadBanner(uri: Uri, contentResolver: ContentResolver, cacheDir: File) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isUploading = true, message = null)
            var tempFile: File? = null
            try {
                val (file, format) = withContext(Dispatchers.IO) {
                    prepareBannerImage(uri, contentResolver, cacheDir)
                }
                tempFile = file
                val requestBody = file.asRequestBody(format.mimeType.toMediaTypeOrNull())
                val part = MultipartBody.Part.createFormData("file", file.name, requestBody)
                repository.uploadBanner(part)
                _uiState.value = _uiState.value.copy(isUploading = false, message = "Banner uploaded")
                loadBanners()
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isUploading = false,
                    message = parseApiError(e, "Upload failed")
                )
            } finally {
                tempFile?.delete()
            }
        }
    }

    private fun prepareBannerImage(
        uri: Uri,
        contentResolver: ContentResolver,
        cacheDir: File
    ): Pair<File, BannerImageFormat> {
        val mimeType = contentResolver.getType(uri)
            ?.substringBefore(';')
            ?.trim()
            ?.lowercase()
            ?: throw IllegalArgumentException("Cannot determine the selected image format")
        val format = when (mimeType) {
            "image/jpeg", "image/jpg" -> BannerImageFormat("image/jpeg", ".jpg")
            "image/png" -> BannerImageFormat("image/png", ".png")
            "image/webp" -> BannerImageFormat("image/webp", ".webp")
            else -> throw IllegalArgumentException("Unsupported image format. Choose JPEG, PNG, or WebP.")
        }

        val file = File.createTempFile("banner_", format.extension, cacheDir)
        try {
            contentResolver.openInputStream(uri).use { input ->
                file.outputStream().use { output ->
                    input?.copyTo(output) ?: throw IllegalStateException("Cannot read the selected image")
                }
            }

            if (file.length() > MAX_BANNER_SIZE_BYTES) {
                throw IllegalArgumentException("Image exceeds the 10 MiB upload limit")
            }
            if (!hasValidImageSignature(file, format.mimeType)) {
                throw IllegalArgumentException("Selected file is not a valid ${format.label()} image")
            }
            return file to format
        } catch (e: Exception) {
            file.delete()
            throw e
        }
    }

    private fun hasValidImageSignature(file: File, mimeType: String): Boolean {
        val header = ByteArray(12)
        val length = file.inputStream().use { it.read(header) }
        return when (mimeType) {
            "image/jpeg" -> length >= 3 &&
                header[0] == 0xFF.toByte() && header[1] == 0xD8.toByte() && header[2] == 0xFF.toByte()
            "image/png" -> length >= 8 &&
                header.copyOfRange(0, 8).contentEquals(byteArrayOf(
                    0x89.toByte(), 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A
                ))
            "image/webp" -> length >= 12 &&
                String(header, 0, 4, Charsets.US_ASCII) == "RIFF" &&
                String(header, 8, 4, Charsets.US_ASCII) == "WEBP"
            else -> false
        }
    }

    private fun BannerImageFormat.label(): String = when (mimeType) {
        "image/jpeg" -> "JPEG"
        "image/png" -> "PNG"
        "image/webp" -> "WebP"
        else -> "supported"
    }

    fun deleteBanner(id: Int) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(message = null)
            runCatching { repository.deleteBanner(id) }
                .onSuccess {
                    _uiState.value = _uiState.value.copy(message = "Banner removed")
                    loadBanners()
                }
                .onFailure { e ->
                    _uiState.value = _uiState.value.copy(
                        message = parseApiError(e, "Delete failed")
                    )
                }
        }
    }

    private fun parseApiError(e: Throwable, defaultMsg: String): String {
        if (e is HttpException) {
            val body = e.response()?.errorBody()?.string().orEmpty()
            val detail = try {
                JSONObject(body).optString("detail")
            } catch (_: Exception) {
                ""
            }
            if (detail.isNotBlank()) return detail
            return "HTTP ${e.code()}"
        }
        return e.message ?: defaultMsg
    }

    private companion object {
        const val MAX_BANNER_SIZE_BYTES = 10L * 1024L * 1024L
    }
}
