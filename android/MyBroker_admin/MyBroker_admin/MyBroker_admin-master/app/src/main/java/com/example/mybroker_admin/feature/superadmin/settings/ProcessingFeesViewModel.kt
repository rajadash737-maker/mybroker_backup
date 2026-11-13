package com.example.mybroker_admin.feature.superadmin.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.remote.dto.ProcessingFeeUpdateRequest
import com.example.mybroker_admin.data.repository.SettingsRepository
import com.example.mybroker_admin.data.repository.SettingsRepositoryImpl
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.json.JSONObject
import retrofit2.HttpException

data class ProcessingFeesUiModel(
    val sellerFee: String = "",
    val buyerFee: String = ""
)

data class ProcessingFeesUiState(
    val data: ProcessingFeesUiModel = ProcessingFeesUiModel(),
    val isLoading: Boolean = false,
    val isSaving: Boolean = false,
    val message: String? = null
)

class ProcessingFeesViewModel(
    private val repository: SettingsRepository = SettingsRepositoryImpl(ApiClient.settingsApi)
) : ViewModel() {

    private val _uiState = MutableStateFlow(ProcessingFeesUiState())
    val uiState: StateFlow<ProcessingFeesUiState> = _uiState.asStateFlow()

    fun loadFees() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, message = null)

            runCatching { repository.getProcessingFees() }
                .onSuccess { dto ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        data = ProcessingFeesUiModel(
                            sellerFee = formatFee(dto.seller_processing_fee),
                            buyerFee = formatFee(dto.buyer_processing_fee)
                        )
                    )
                }
                .onFailure { e ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        message = parseApiError(e, "Failed to load processing fees")
                    )
                }
        }
    }

    fun onSellerFeeChange(v: String) = updateData { it.copy(sellerFee = v) }
    fun onBuyerFeeChange(v: String) = updateData { it.copy(buyerFee = v) }

    fun saveFees() {
        val data = _uiState.value.data
        val seller = data.sellerFee.trim().toDoubleOrNull()
        val buyer = data.buyerFee.trim().toDoubleOrNull()

        if (seller == null || buyer == null || seller < 0 || buyer < 0) {
            _uiState.value = _uiState.value.copy(message = "Please enter valid fee amounts")
            return
        }

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isSaving = true, message = null)

            runCatching {
                repository.updateProcessingFees(
                    ProcessingFeeUpdateRequest(
                        seller_processing_fee = seller,
                        buyer_processing_fee = buyer
                    )
                )
            }.onSuccess {
                _uiState.value = _uiState.value.copy(isSaving = false, message = "Fees updated")
                loadFees()
            }.onFailure { e ->
                _uiState.value = _uiState.value.copy(
                    isSaving = false,
                    message = parseApiError(e, "Update failed")
                )
            }
        }
    }

    private fun updateData(block: (ProcessingFeesUiModel) -> ProcessingFeesUiModel) {
        _uiState.value = _uiState.value.copy(data = block(_uiState.value.data))
    }

    private fun formatFee(value: Double): String {
        return if (value % 1.0 == 0.0) value.toInt().toString() else value.toString()
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
