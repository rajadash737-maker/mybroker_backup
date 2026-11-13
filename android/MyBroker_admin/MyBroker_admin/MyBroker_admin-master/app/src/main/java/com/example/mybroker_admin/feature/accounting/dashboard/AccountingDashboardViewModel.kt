package com.example.mybroker_admin.feature.accounting.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.repository.AdminListingRepository
import com.example.mybroker_admin.data.repository.AccountingListingRepository
import com.example.mybroker_admin.data.repository.ProfileRepositoryImpl
import com.example.mybroker_admin.feature.accounting.dashboard.components.AccountingDashboardState
import com.example.mybroker_admin.feature.accounting.dashboard.components.AccountingRevenueRangeType
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

class AccountingDashboardViewModel : ViewModel() {

    private val profileRepo = ProfileRepositoryImpl(ApiClient.profileApi)
    private val accountingRepo = AccountingListingRepository(ApiClient.accountingListingApi)
    private val adminListingRepo = AdminListingRepository(ApiClient.adminListingApi)

    private val _state = MutableStateFlow(
        AccountingDashboardState(
            totalRevenue = 0.0,
            pendingPayments = 0,
            completedTransactions = 0,
            pendingRefunds = 0
        )
    )
    val state: StateFlow<AccountingDashboardState> = _state

    init {
        loadProfile()
        loadSummary()
    }

    fun refresh() {
        loadProfile()
        loadSummary()
    }

    fun setRange(type: AccountingRevenueRangeType) {
        _state.update { it.copy(rangeType = type) }
        if (type != AccountingRevenueRangeType.CUSTOM) {
            loadSummary()
        }
    }

    fun updateCustomStart(value: String) {
        _state.update { it.copy(customStart = value) }
    }

    fun updateCustomEnd(value: String) {
        _state.update { it.copy(customEnd = value) }
    }

    fun applyCustomRange() {
        loadSummary()
    }

    private fun loadProfile() {
        viewModelScope.launch {
            runCatching { profileRepo.getMyProfile() }
                .onSuccess { p ->
                    _state.update {
                        it.copy(
                            accountantName = p.fullname,
                            profileImageUrl = p.profileImageUrl
                        )
                    }
                }
        }
    }

    fun loadSummary() {
        val current = _state.value
        val range = current.rangeType.value
        val start = if (current.rangeType == AccountingRevenueRangeType.CUSTOM) current.customStart.takeIf { it.isNotBlank() } else null
        val end = if (current.rangeType == AccountingRevenueRangeType.CUSTOM) current.customEnd.takeIf { it.isNotBlank() } else null

        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, errorMessage = null) }
            runCatching { accountingRepo.getDashboardSummary(range = range, start = start, end = end) }
                .onSuccess { summary ->
                    val webhookCount = runCatching { adminListingRepo.getWebhookLogsCount() }
                        .getOrDefault(_state.value.webhookLogCount)
                    _state.update {
                        it.copy(
                            isLoading = false,
                            totalRevenue = summary.total_revenue,
                            pendingPayments = summary.pending_payments,
                            completedTransactions = summary.completed_transactions,
                            pendingRefunds = summary.pending_refunds,
                            webhookLogCount = webhookCount
                        )
                    }
                }
                .onFailure { err ->
                    _state.update {
                        it.copy(isLoading = false, errorMessage = err.message ?: "Failed to load dashboard")
                    }
                }
        }
    }
}
