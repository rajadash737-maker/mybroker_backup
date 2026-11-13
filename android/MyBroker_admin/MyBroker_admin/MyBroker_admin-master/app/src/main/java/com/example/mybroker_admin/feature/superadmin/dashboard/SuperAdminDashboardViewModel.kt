package com.example.mybroker_admin.feature.superadmin.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.repository.AccountingListingRepository
import com.example.mybroker_admin.data.repository.AdminListingRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

enum class RevenueRangeType(val value: String) {
    ALL("all"),
    TODAY("today"),
    WEEK("week"),
    MONTH("month"),
    CUSTOM("custom")
}

data class RevenueTransaction(
    val date: String,
    val type: String,
    val userName: String,
    val amount: Double,
    val status: String
)

data class DashboardState(
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val rangeType: RevenueRangeType = RevenueRangeType.MONTH,
    val customStart: String = "",
    val customEnd: String = "",
    val totalRevenue: Double = 0.0,
    val sellerRevenue: Double = 0.0,
    val buyerRevenue: Double = 0.0,
    val transactions: List<RevenueTransaction> = emptyList(),
    val totalListings: Int = 0,
    val pendingAdminReview: Int? = null,
    val isPendingCountLoading: Boolean = false,
    val pendingCountErrorMessage: String? = null
)

class SuperAdminDashboardViewModel : ViewModel() {

    private val repo = AccountingListingRepository(ApiClient.accountingListingApi)
    private val listingRepo = AdminListingRepository(ApiClient.adminListingApi)

    private val _state = MutableStateFlow(DashboardState())
    val state: StateFlow<DashboardState> = _state

    init {
        loadRevenue()
        loadTotalListings()
        loadPendingCount()
    }

    fun refresh() {
        loadRevenue()
        loadTotalListings()
        loadPendingCount()
    }

    fun setRange(type: RevenueRangeType) {
        _state.update { it.copy(rangeType = type) }
        if (type != RevenueRangeType.CUSTOM) {
            loadRevenue()
        }
    }

    fun updateCustomStart(value: String) {
        _state.update { it.copy(customStart = value) }
    }

    fun updateCustomEnd(value: String) {
        _state.update { it.copy(customEnd = value) }
    }

    fun applyCustomRange() {
        loadRevenue()
    }

    fun loadRevenue() {
        val current = _state.value
        val range = current.rangeType.value
        val start = if (current.rangeType == RevenueRangeType.CUSTOM) current.customStart.takeIf { it.isNotBlank() } else null
        val end = if (current.rangeType == RevenueRangeType.CUSTOM) current.customEnd.takeIf { it.isNotBlank() } else null

        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, errorMessage = null) }
            runCatching { repo.getSuperAdminRevenueDashboard(range = range, start = start, end = end) }
                .onSuccess { res ->
                    _state.update {
                        it.copy(
                            isLoading = false,
                            totalRevenue = res.revenue.total,
                            sellerRevenue = res.revenue.seller,
                            buyerRevenue = res.revenue.buyer,
                            transactions = res.transactions.map { txn ->
                                RevenueTransaction(
                                    date = txn.date,
                                    type = txn.type,
                                    userName = txn.user_name,
                                    amount = txn.amount,
                                    status = txn.status
                                )
                            }
                        )
                    }
                }
                .onFailure { err ->
                    _state.update {
                        it.copy(isLoading = false, errorMessage = err.message ?: "Failed to load revenue")
                    }
                }
        }
    }

    private fun loadTotalListings() {
        viewModelScope.launch {
            runCatching { listingRepo.getAllListingsCount() }
                .onSuccess { total ->
                    _state.update { it.copy(totalListings = total) }
                }
                .onFailure { _ ->
                    _state.update { it.copy(totalListings = 0) }
                }
        }
    }

    private fun loadPendingCount() {
        viewModelScope.launch {
            _state.update { it.copy(isPendingCountLoading = true, pendingCountErrorMessage = null) }
            runCatching { listingRepo.getWorkflowSummary() }
                .onSuccess { summary ->
                    _state.update {
                        it.copy(
                            pendingAdminReview = summary.pending_admin_review,
                            isPendingCountLoading = false,
                            pendingCountErrorMessage = null
                        )
                    }
                }
                .onFailure {
                    _state.update {
                        it.copy(
                            isPendingCountLoading = false,
                            pendingCountErrorMessage = "Pending count unavailable"
                        )
                    }
                }
        }
    }
}
