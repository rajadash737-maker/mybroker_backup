package com.example.mybroker_admin.feature.superadmin.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.remote.dto.SocialLinksUpdateRequest
import com.example.mybroker_admin.data.repository.SettingsRepository
import com.example.mybroker_admin.data.repository.SettingsRepositoryImpl
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.json.JSONObject
import retrofit2.HttpException

data class SocialLinksUiModel(
    val whatsapp: String = "",
    val instagram: String = "",
    val telegram: String = "",
    val youtube: String = "",
    val facebook: String = "",
    val linkedin: String = ""
)

data class SocialLinksUiState(
    val data: SocialLinksUiModel = SocialLinksUiModel(),
    val isLoading: Boolean = false,
    val isSaving: Boolean = false,
    val message: String? = null
)

class SettingsViewModel(
    private val repository: SettingsRepository = SettingsRepositoryImpl(ApiClient.settingsApi)
) : ViewModel() {

    private val _uiState = MutableStateFlow(SocialLinksUiState())
    val uiState: StateFlow<SocialLinksUiState> = _uiState.asStateFlow()

    fun loadLinks() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, message = null)

            runCatching { repository.getSocialLinks() }
                .onSuccess { dto ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        data = SocialLinksUiModel(
                            whatsapp = dto.whatsapp.orEmpty(),
                            instagram = dto.instagram.orEmpty(),
                            telegram = dto.telegram.orEmpty(),
                            youtube = dto.youtube.orEmpty(),
                            facebook = dto.facebook.orEmpty(),
                            linkedin = dto.linkedin.orEmpty()
                        )
                    )
                }
                .onFailure { e ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        message = parseApiError(e, "Failed to load links")
                    )
                }
        }
    }

    fun onWhatsappChange(v: String) = updateData { it.copy(whatsapp = v) }
    fun onInstagramChange(v: String) = updateData { it.copy(instagram = v) }
    fun onTelegramChange(v: String) = updateData { it.copy(telegram = v) }
    fun onYoutubeChange(v: String) = updateData { it.copy(youtube = v) }
    fun onFacebookChange(v: String) = updateData { it.copy(facebook = v) }
    fun onLinkedinChange(v: String) = updateData { it.copy(linkedin = v) }

    fun saveLinks() {
        val d = _uiState.value.data
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isSaving = true, message = null)

            runCatching {
                repository.updateSocialLinks(
                    SocialLinksUpdateRequest(
                        whatsapp = d.whatsapp.trim().ifEmpty { null },
                        instagram = d.instagram.trim().ifEmpty { null },
                        telegram = d.telegram.trim().ifEmpty { null },
                        youtube = d.youtube.trim().ifEmpty { null },
                        facebook = d.facebook.trim().ifEmpty { null },
                        linkedin = d.linkedin.trim().ifEmpty { null }
                    )
                )
            }.onSuccess {
                _uiState.value = _uiState.value.copy(isSaving = false, message = "Links updated")
                loadLinks()
            }.onFailure { e ->
                _uiState.value = _uiState.value.copy(
                    isSaving = false,
                    message = parseApiError(e, "Update failed")
                )
            }
        }
    }

    private fun updateData(block: (SocialLinksUiModel) -> SocialLinksUiModel) {
        _uiState.value = _uiState.value.copy(data = block(_uiState.value.data))
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
}

