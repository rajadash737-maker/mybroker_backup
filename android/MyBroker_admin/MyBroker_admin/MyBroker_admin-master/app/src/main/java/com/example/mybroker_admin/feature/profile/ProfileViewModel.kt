package com.example.mybroker_admin.feature.profile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.core.session.SessionManager
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.repository.ProfileRepository
import com.example.mybroker_admin.data.repository.ProfileRepositoryImpl
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import retrofit2.HttpException
import java.io.File

class ProfileViewModel(
    private val repository: ProfileRepository = ProfileRepositoryImpl(ApiClient.profileApi)
) : ViewModel() {

    private val _uiState = MutableStateFlow(ProfileUiState())
    val uiState: StateFlow<ProfileUiState> = _uiState.asStateFlow()

    fun loadProfile() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, message = null)

            runCatching { repository.getMyProfile() }
                .onSuccess { dto ->
                    val (district, state) = splitAddress(dto.address)
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        data = ProfileUiModel(
                            id = dto.id,
                            fullName = dto.fullname,
                            mobile = dto.mobile.orEmpty(),
                            district = district,
                            state = state,
                            role = dto.role,
                            profileImageUrl = ApiClient.absoluteUrl(dto.profileImageUrl)
                        )
                    )
                    SessionManager.updateUserIdentity(
                        fullName = dto.fullname,
                        role = dto.role
                    )
                }
                .onFailure { e ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        message = parseApiError(e, "Profile load failed")
                    )
                }
        }
    }

    fun onFullNameChange(v: String) = updateData { it.copy(fullName = v) }
    fun onMobileChange(v: String) = updateData { it.copy(mobile = v) }
    fun onStateChange(v: String) = updateData { it.copy(state = v) }
    fun onDistrictChange(v: String) = updateData { it.copy(district = v) }

    fun saveProfile() {
        val d = _uiState.value.data
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isSaving = true, message = null)

            runCatching {
                repository.updateMyProfile(
                    fullname = d.fullName.trim(),
                    mobile = d.mobile.trim(),
                    address = joinAddress(d.district, d.state)
                )
            }.onSuccess {
                _uiState.value = _uiState.value.copy(isSaving = false, message = "Profile updated")
                SessionManager.updateUserIdentity(fullName = d.fullName.trim())
                loadProfile()
            }.onFailure { e ->
                _uiState.value = _uiState.value.copy(
                    isSaving = false,
                    message = parseApiError(e, "Profile update failed")
                )
            }
        }
    }

    fun uploadPhoto(file: File) {
        viewModelScope.launch {
            val req = file.readBytes().toRequestBody("image/*".toMediaTypeOrNull())
            val part = MultipartBody.Part.createFormData("file", file.name, req)

            runCatching { repository.uploadProfilePhoto(part) }
                .onSuccess { url ->
                    updateData { it.copy(profileImageUrl = ApiClient.absoluteUrl(url)) }
                    _uiState.value = _uiState.value.copy(message = "Profile photo updated")
                }
                .onFailure { e ->
                    _uiState.value = _uiState.value.copy(
                        message = parseApiError(e, "Photo upload failed")
                    )
                }
        }
    }

    private fun updateData(block: (ProfileUiModel) -> ProfileUiModel) {
        _uiState.value = _uiState.value.copy(data = block(_uiState.value.data))
    }

    private fun splitAddress(address: String?): Pair<String, String> {
        if (address.isNullOrBlank()) return "" to ""
        val parts = address.split(",").map { it.trim() }
        return if (parts.size >= 2) parts[0] to parts[1] else address to ""
    }

    private fun joinAddress(district: String, state: String): String {
        return listOf(district.trim(), state.trim())
            .filter { it.isNotEmpty() }
            .joinToString(", ")
    }

    private fun parseApiError(e: Throwable, defaultMsg: String): String {
        if (e is HttpException) {
            val body = e.response()?.errorBody()?.string().orEmpty()
            val detail = try {
                JSONObject(body).optString("detail")
            } catch (_: Exception) {
                ""
            }

            if (e.code() == 409 && detail.contains("already in use", ignoreCase = true)) {
                return "Ye mobile number pehle se kisi aur account me use ho raha hai."
            }
            if (detail.isNotBlank()) return detail
            return "HTTP ${e.code()}"
        }
        return e.message ?: defaultMsg
    }
}
