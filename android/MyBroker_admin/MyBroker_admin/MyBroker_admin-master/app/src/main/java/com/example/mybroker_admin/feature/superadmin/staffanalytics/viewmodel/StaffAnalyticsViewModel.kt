package com.example.mybroker_admin.feature.superadmin.staffanalytics.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.core.session.SessionManager
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.repository.StaffAnalyticsRepositoryImpl
import com.example.mybroker_admin.feature.superadmin.staffanalytics.model.StaffAnalyticsDateFilter
import com.example.mybroker_admin.feature.superadmin.staffanalytics.model.StaffAnalyticsItem
import com.example.mybroker_admin.feature.superadmin.staffanalytics.model.StaffAnalyticsRoleTab
import com.example.mybroker_admin.feature.superadmin.staffanalytics.model.StaffAnalyticsSummary
import com.example.mybroker_admin.feature.superadmin.staffanalytics.model.StaffAnalyticsUiState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

class StaffAnalyticsViewModel : ViewModel() {

    private val repo = StaffAnalyticsRepositoryImpl(ApiClient.staffAnalyticsApi)

    private val _state = MutableStateFlow(StaffAnalyticsUiState())
    val state: StateFlow<StaffAnalyticsUiState> = _state

    init {
        loadAnalytics()
    }

    fun onRoleTabSelected(tab: StaffAnalyticsRoleTab) {
        _state.update { it.copy(selectedRoleTab = tab) }
        loadAnalytics()
    }

    fun onDateFilterSelected(filter: StaffAnalyticsDateFilter) {
        _state.update { it.copy(dateFilter = filter, filterMessage = null) }
        if (filter != StaffAnalyticsDateFilter.CUSTOM) {
            loadAnalytics()
        }
    }

    fun onCustomStartChange(value: String) {
        _state.update { it.copy(customStart = value) }
    }

    fun onCustomEndChange(value: String) {
        _state.update { it.copy(customEnd = value) }
    }

    fun applyCustomRange() {
        if (_state.value.dateFilter != StaffAnalyticsDateFilter.CUSTOM) return
        val start = _state.value.customStart.trim()
        val end = _state.value.customEnd.trim()
        if (start.isBlank() || end.isBlank()) {
            _state.update { it.copy(filterMessage = "Please select the range") }
            return
        }
        _state.update { it.copy(filterMessage = null) }
        loadAnalytics()
    }

    private fun loadAnalytics() {
        val token = SessionManager.accessToken
        if (token.isNullOrBlank()) {
            _state.update { it.copy(error = "Session expired. Login again.") }
            return
        }

        _state.update { it.copy(isLoading = true, error = null) }

        val roleParam = when (_state.value.selectedRoleTab) {
            StaffAnalyticsRoleTab.ALL -> null
            StaffAnalyticsRoleTab.ADMIN -> "ADMIN"
            StaffAnalyticsRoleTab.FIELD_OFFICER -> "FIELD_OFFICER"
        }

        val rangeParam = when (_state.value.dateFilter) {
            StaffAnalyticsDateFilter.ALL -> "all"
            StaffAnalyticsDateFilter.TODAY -> "today"
            StaffAnalyticsDateFilter.WEEK -> "week"
            StaffAnalyticsDateFilter.MONTH -> "month"
            StaffAnalyticsDateFilter.CUSTOM -> "custom"
        }

        val startDate = _state.value.customStart.trim().ifBlank { null }
        val endDate = _state.value.customEnd.trim().ifBlank { null }

        viewModelScope.launch {
            try {
                val response = repo.getStaffAnalytics(
                    accessToken = token,
                    role = roleParam,
                    range = rangeParam,
                    startDate = if (rangeParam == "custom") startDate else null,
                    endDate = if (rangeParam == "custom") endDate else null
                )

                val summary = StaffAnalyticsSummary(
                    totalStaffCount = response.summary.total_staff,
                    totalSiteVisits = response.summary.total_visits,
                    totalVerifiedDocuments = response.summary.total_verified_docs,
                    totalRejectedDocuments = response.summary.total_rejected_docs
                )

                val staff = response.staff.map { item ->
                    StaffAnalyticsItem(
                        id = item.id,
                        name = item.name,
                        mobile = item.mobile,
                        role = item.role,
                        documentsVerifiedCount = item.documents_verified ?: 0,
                        documentsRejectedCount = item.documents_rejected ?: 0,
                        listingsApproved = item.listings_approved ?: 0,
                        registryApprovedCount = item.registry_approved ?: 0,
                        soldCount = item.sold_count ?: 0,
                        siteVisitsCount = item.site_visits ?: 0,
                        registryVisitsCount = item.registry_visits ?: 0
                    )
                }

                _state.update {
                    it.copy(
                        isLoading = false,
                        summary = summary,
                        staff = staff
                    )
                }
            } catch (e: Exception) {
                _state.update { it.copy(isLoading = false, error = e.message ?: "Failed to load analytics") }
            }
        }
    }
}
