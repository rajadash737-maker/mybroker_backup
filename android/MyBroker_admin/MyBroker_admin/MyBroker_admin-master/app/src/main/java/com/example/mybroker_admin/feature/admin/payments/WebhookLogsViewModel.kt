package com.example.mybroker_admin.feature.admin.payments

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.remote.dto.WebhookLogItemDto
import com.example.mybroker_admin.data.repository.AdminListingRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Locale

data class WebhookLogUi(
    val id: Int,
    val event: String,
    val eventId: String?,
    val orderId: String?,
    val paymentId: String?,
    val status: String,
    val paymentContext: String,
    val error: String?,
    val payload: String,
    val createdAt: String
)

data class WebhookLogsState(
    val loaded: Boolean = false,
    val isLoading: Boolean = false,
    val error: String? = null,
    val items: List<WebhookLogUi> = emptyList(),
    val total: Int = 0,
    val selectedContext: String? = null,
    val selectedStatus: String? = null
)

class WebhookLogsViewModel : ViewModel() {
    private val repo = AdminListingRepository(ApiClient.adminListingApi)

    private val _state = MutableStateFlow(WebhookLogsState())
    val state: StateFlow<WebhookLogsState> = _state.asStateFlow()

    fun load() = viewModelScope.launch {
        val current = _state.value
        _state.value = current.copy(isLoading = true, error = null)

        runCatching {
            repo.getWebhookLogs(
                skip = 0,
                limit = 50,
                paymentContext = current.selectedContext,
                status = current.selectedStatus
            )
        }.onSuccess { res ->
            _state.value = current.copy(
                loaded = true,
                isLoading = false,
                error = null,
                total = res.total,
                items = res.items.map { mapLog(it) }
            )
        }.onFailure { err ->
            _state.value = current.copy(
                loaded = true,
                isLoading = false,
                error = err.message ?: "Failed to load webhook logs"
            )
        }
    }

    fun updateContextFilter(value: String?) {
        _state.value = _state.value.copy(selectedContext = value)
        load()
    }

    fun updateStatusFilter(value: String?) {
        _state.value = _state.value.copy(selectedStatus = value)
        load()
    }

    private fun mapLog(dto: WebhookLogItemDto): WebhookLogUi {
        return WebhookLogUi(
            id = dto.id,
            event = dto.event.replace("_", " ").uppercase(),
            eventId = dto.eventId,
            orderId = dto.orderId,
            paymentId = dto.paymentId,
            status = dto.status.replace("_", " ").uppercase(),
            paymentContext = dto.paymentContext.replace("_", " ").uppercase(),
            error = dto.error,
            payload = dto.payload,
            createdAt = formatDateTime(dto.createdAt)
        )
    }

    private fun formatDateTime(raw: String?): String {
        if (raw.isNullOrBlank()) return "-"
        val cleaned = raw.trim()
            .replace("Z", "")
            .replace(Regex("[+-]\\d{2}:?\\d{2}$"), "")
            .let { value ->
                val dot = value.indexOf(".")
                if (dot >= 0) value.substring(0, dot) else value
            }

        val inputFormats = listOf(
            SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.ENGLISH),
            SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.ENGLISH)
        )
        val output = SimpleDateFormat("dd MMM yyyy, hh.mm a", Locale.ENGLISH)

        for (fmt in inputFormats) {
            runCatching {
                val date = fmt.parse(cleaned) ?: return@runCatching
                return output.format(date).replace("AM", "am").replace("PM", "pm")
            }
        }
        return raw
    }
}
