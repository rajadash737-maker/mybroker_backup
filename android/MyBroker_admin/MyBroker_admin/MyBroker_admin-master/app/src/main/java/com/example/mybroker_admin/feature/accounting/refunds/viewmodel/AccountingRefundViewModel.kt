package com.example.mybroker_admin.feature.accounting.refunds.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.repository.AccountingListingRepository
import com.example.mybroker_admin.feature.accounting.refunds.model.RefundItem
import com.example.mybroker_admin.feature.accounting.refunds.model.RefundStatus
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class AccountingRefundState(
    val isLoading: Boolean = false,
    val isConfirming: Boolean = false,
    val errorMessage: String? = null,
    val successMessage: String? = null,
    val pending: List<RefundItem> = emptyList(),
    val history: List<RefundItem> = emptyList()
)

class AccountingRefundViewModel(
    private val repository: AccountingListingRepository
) : ViewModel() {

    constructor() : this(
        AccountingListingRepository(ApiClient.accountingListingApi)
    )

    private val _state = MutableStateFlow(AccountingRefundState())
    val state: StateFlow<AccountingRefundState> = _state

    init {
        loadPendingRefunds()
        loadRefundHistory()
    }

    fun clearError() {
        _state.update { it.copy(errorMessage = null) }
    }

    fun clearSuccess() {
        _state.update { it.copy(successMessage = null) }
    }

    fun loadPendingRefunds() {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, errorMessage = null) }

            runCatching { repository.getPendingRefunds(skip = 0, limit = 50) }
                .onSuccess { response ->
                    val mapped = response.items.map { item ->
                        RefundItem(
                            id = item.request_id,
                            listingId = "LST-${item.request_id}",
                            sellerName = item.seller_fullname,
                            sellerMobile = item.seller_mobile,
                            isAdminInvolved = item.admin_involved,
                            adminName = item.admin_name,
                            adminMobile = item.admin_mobile,
                            adminStatus = item.admin_status,
                            totalPaid = item.total_paid.toInt(),
                            cancelDate = item.cancelled_at,
                            sellerUpiId = item.refund_upi_id,
                            cancelReason = item.cancellation_reason,
                            status = RefundStatus.PENDING
                        )
                    }
                    _state.update { it.copy(isLoading = false, pending = mapped) }
                }
                .onFailure { e ->
                    _state.update {
                        it.copy(
                            isLoading = false,
                            pending = emptyList(),
                            errorMessage = e.message ?: "Failed to load pending refunds"
                        )
                    }
                }
        }
    }

    fun loadRefundHistory() {
        viewModelScope.launch {
            runCatching { repository.getRefundHistory(skip = 0, limit = 50) }
                .onSuccess { response ->
                    val mapped = response.items.map { item ->
                        RefundItem(
                            id = item.request_id,
                            listingId = "LST-${item.request_id}",
                            sellerName = item.seller_fullname,
                            sellerMobile = item.seller_mobile,
                            isAdminInvolved = item.admin_involved,
                            adminName = item.admin_name,
                            adminMobile = item.admin_mobile,
                            adminStatus = item.admin_status,
                            totalPaid = item.total_paid.toInt(),
                            cancelDate = item.cancelled_at,
                            sellerUpiId = item.refund_upi_id,
                            cancelReason = item.cancellation_reason,
                            refundAmount = item.refund_amount?.toInt(),
                            transactionId = item.refund_transaction_id,
                            refundedDate = item.refund_completed_at,
                            status = RefundStatus.SUCCESS
                        )
                    }
                    _state.update { it.copy(history = mapped) }
                }
                .onFailure { e ->
                    _state.update { it.copy(errorMessage = e.message ?: "Failed to load refund history") }
                }
        }
    }

    fun confirmRefund(id: Int, amount: Int, txnId: String) {
        viewModelScope.launch {
            _state.update { it.copy(isConfirming = true, errorMessage = null, successMessage = null) }

            runCatching { repository.confirmRefund(id, amount, txnId) }
                .onSuccess { result ->
                    val moved = _state.value.pending.firstOrNull { it.id == id } ?: return@onSuccess
                    val updated = moved.copy(
                        refundAmount = (result.refund_amount ?: amount.toDouble()).toInt(),
                        transactionId = result.refund_transaction_id ?: txnId,
                        refundedDate = result.refund_completed_at,
                        status = RefundStatus.SUCCESS
                    )
                    _state.update {
                        it.copy(
                            isConfirming = false,
                            pending = it.pending.filterNot { item -> item.id == id },
                            history = listOf(updated) + it.history,
                            successMessage = result.status
                        )
                    }
                }
                .onFailure { e ->
                    _state.update {
                        it.copy(
                            isConfirming = false,
                            errorMessage = e.message ?: "Failed to confirm refund"
                        )
                    }
                }
        }
    }
}
