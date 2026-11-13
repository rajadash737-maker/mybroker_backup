package com.example.mybroker_admin.feature.superadmin.listings.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.remote.dto.AdminListingItemDto
import com.example.mybroker_admin.data.repository.AdminListingRepository
import com.example.mybroker_admin.feature.superadmin.listings.model.SuperAdminListingItem
import com.example.mybroker_admin.feature.superadmin.listings.model.SuperAdminListingFilters
import com.example.mybroker_admin.feature.superadmin.listings.model.SuperAdminListingsState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

class SuperAdminListingsViewModel : ViewModel() {

    private val repo = AdminListingRepository(ApiClient.adminListingApi)
    private val pageSize = 20
    private var currentSkip = 0

    private val _state = MutableStateFlow(SuperAdminListingsState())
    val state: StateFlow<SuperAdminListingsState> = _state

    init {
        loadListings(reset = true)
    }

    private fun mapItem(item: AdminListingItemDto): SuperAdminListingItem {
        return SuperAdminListingItem(
            id = item.id,
            sellerName = item.owner_name ?: "N/A",
            sellerMobile = item.owner_mobile ?: "N/A",
            status = item.status.uppercase()
        )
    }

    fun onSearchQueryChange(value: String) {
        _state.update { it.copy(searchQuery = value) }
    }

    fun onStatusSelected(status: String?) {
        _state.update { it.copy(statusFilter = status) }
        loadListings(reset = true)
    }

    fun applySearch() {
        loadListings(reset = true)
    }

    fun loadListings(reset: Boolean) {
        if (reset) {
            currentSkip = 0
            _state.update {
                it.copy(
                    isLoading = true,
                    error = null,
                    listings = emptyList(),
                    canLoadMore = true
                )
            }
        } else {
            if (!_state.value.canLoadMore || _state.value.isLoadingMore) return
            _state.update { it.copy(isLoadingMore = true, error = null) }
        }

        viewModelScope.launch {
            val query = _state.value.searchQuery.trim().ifBlank { null }
            val numeric = query?.all { it.isDigit() } == true
            val listingId = if (numeric && (query?.length ?: 0) <= 6) query?.toIntOrNull() else null
            val searchText = if (listingId != null) null else query
            val status = _state.value.statusFilter
            val skip = if (reset) 0 else currentSkip
            runCatching {
                repo.getAllListings(
                    skip = skip,
                    limit = pageSize,
                    search = searchText,
                    status = status,
                    listingId = listingId
                )
            }
                .onSuccess { res ->
                    val mapped = SuperAdminListingFilters.filterPage(
                        res.items.map { item -> mapItem(item) },
                        _state.value.statusFilter
                    )
                    currentSkip = skip + res.items.size
                    _state.update { st ->
                        st.copy(
                            isLoading = false,
                            isLoadingMore = false,
                            listings = if (reset) mapped else st.listings + mapped,
                            canLoadMore = currentSkip < res.total
                        )
                    }
                }
                .onFailure { err ->
                    _state.update {
                        it.copy(
                            isLoading = false,
                            isLoadingMore = false,
                            error = err.message ?: "Failed to load listings"
                        )
                    }
                }
        }
    }

    fun loadMore() {
        loadListings(reset = false)
    }
}
