package com.example.mybroker_admin.feature.admin.dashboard.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.repository.AdminListingRepository
import com.example.mybroker_admin.feature.admin.dashboard.model.DashboardStats
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class AdminDashboardViewModel : ViewModel() {
    private val repo = AdminListingRepository(ApiClient.adminListingApi)

    private val _stats = MutableStateFlow(DashboardStats())
    val stats: StateFlow<DashboardStats> = _stats.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    init { loadStats() }

    fun loadStats() = viewModelScope.launch {
        _isLoading.value = true
        _error.value = null

        runCatching {
            val s = repo.getWorkflowSummary()
            DashboardStats(
                pendingCount = s.pending_admin_review,
                assignedCount = s.assigned_to_field_officer,
                fieldVerifiedCount = s.field_verified_final_approval,
                liveCount = s.live_listings,
                lockedCount = s.locked_listings,
                bookedCount = s.booked_listings,
                soldCount = s.sold_listings,
                rejectedCount = s.rejected_listings,
                cancelPendingCount = s.cancel_refund_management,
                pendingRegistryVerificationCount = s.pending_registry_verification,
                refundSuccessCount = 0,
                adminName = s.viewer?.fullname ?: "Admin",
                profileImageUrl = ApiClient.absoluteUrl(s.viewer?.profileImageUrl)
            )
        }.onSuccess {
            _stats.value = it
        }.onFailure {
            _error.value = it.message ?: "Failed to load dashboard"
        }

        _isLoading.value = false
    }
}
