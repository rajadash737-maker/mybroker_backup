package com.example.mybroker_admin.feature.admin.cancel.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.repository.AdminListingRepository
import com.example.mybroker_admin.feature.admin.cancel.presentation.state.CancelRefundState
import com.example.mybroker_admin.feature.admin.cancel.presentation.state.RefundTab
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class RefundUiModel(
    val id: Int,
    val listingId: String,
    val sellerName: String,
    val sellerMobile: String,
    val documentVerified: Boolean,
    val fieldVisitDone: Boolean,
    val listingLive: Boolean,
    val cancelDate: String,
    val cancelReason: String = "",
    val refundDate: String? = null,
    val refundStatus: String? = null,
    val sellerCurrentStatus: String? = null
)

class CancelRefundViewModel(
    private val repository: AdminListingRepository
) : ViewModel() {

    constructor() : this(
        AdminListingRepository(ApiClient.adminListingApi)
    )

    private val _state = MutableStateFlow(CancelRefundState())
    val state: StateFlow<CancelRefundState> = _state

    init {
        loadPendingRefunds()
        loadSuccessRefunds()
    }

    fun onTabSelected(tab: RefundTab) {
        _state.update { it.copy(selectedTab = tab) }
        if (tab == RefundTab.SUCCESS && _state.value.successList.isEmpty()) {
            loadSuccessRefunds()
        }
    }

    fun clearError() {
        _state.update { it.copy(errorMessage = null) }
    }

    fun clearSuccess() {
        _state.update { it.copy(successMessage = null) }
    }

    fun loadPendingRefunds() {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, errorMessage = null, successMessage = null) }

            runCatching { repository.getPendingAdminRefunds(skip = 0, limit = 50) }
                .onSuccess { response ->
                    val mapped = response.items.map { item ->
                        RefundUiModel(
                            id = item.request_id,
                            listingId = item.listing_code ?: "-",
                            sellerName = item.seller.fullname,
                            sellerMobile = item.seller.mobile,
                            documentVerified = true,
                            fieldVisitDone = false,
                            listingLive = false,
                            cancelDate = item.cancelled_at,
                            cancelReason = item.cancellation_reason
                        )
                    }
                    _state.update {
                        it.copy(
                            isLoading = false,
                            pendingList = mapped,
                            errorMessage = null
                        )
                    }
                }
                .onFailure { e ->
                    _state.update {
                        it.copy(
                            isLoading = false,
                            pendingList = emptyList(),
                            errorMessage = e.message ?: "Failed to load pending refunds"
                        )
                    }
                }
        }
    }

    fun loadSuccessRefunds() {
        viewModelScope.launch {
            runCatching { repository.getSuccessAdminRefunds(skip = 0, limit = 50) }
                .onSuccess { response ->
                    val mapped = response.items.map { item ->
                        val statusAtCancellation =
                            item.status_before_cancellation_label
                                ?: item.cancellation_stage
                                ?: item.status_before_cancellation
                                ?: "-"

                        RefundUiModel(
                            id = item.request_id,
                            listingId = item.listing_code ?: "-",
                            sellerName = item.seller.fullname,
                            sellerMobile = item.seller.mobile,
                            documentVerified = true,
                            fieldVisitDone = true,
                            listingLive = false,
                            cancelDate = item.cancelled_at,
                            cancelReason = item.cancellation_reason,
                            refundDate = item.refund_completed_at,
                            refundStatus = item.status,
                            sellerCurrentStatus = statusAtCancellation
                        )
                    }
                    _state.update { it.copy(successList = mapped) }
                }
                .onFailure { e ->
                    _state.update { it.copy(errorMessage = e.message ?: "Failed to load successful refunds") }
                }
        }
    }

    fun forwardToAccounting(id: Int) {
        viewModelScope.launch {
            _state.update { it.copy(isForwarding = true, errorMessage = null, successMessage = null) }

            runCatching { repository.forwardRefundToAccounting(id) }
                .onSuccess { result ->
                    _state.update { current ->
                        current.copy(
                            isForwarding = false,
                            pendingList = current.pendingList.filterNot { it.id == id },
                            errorMessage = null,
                            successMessage = result.status
                        )
                    }
                    loadSuccessRefunds()
                }
                .onFailure { e ->
                    _state.update {
                        it.copy(
                            isForwarding = false,
                            errorMessage = e.message ?: "Failed to forward to accounting"
                        )
                    }
                }
        }
    }
}
