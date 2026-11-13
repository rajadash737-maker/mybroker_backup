package com.example.mybroker_admin.feature.admin.listings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.data.repository.AdminListingRepository
import com.example.mybroker_admin.data.remote.ApiClient
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class RegistryPendingUi(
    val bookingId: Int,
    val listingId: Int,
    val sellerName: String?,
    val sellerMobile: String?,
    val buyerName: String,
    val buyerMobile: String,
    val registryDate: String?,
    val registryTime: String?,
    val registryLocation: String?,
    val proofUrl: String?
)

data class RegistryPendingState(
    val loaded: Boolean = false,
    val isLoading: Boolean = false,
    val error: String? = null,
    val items: List<RegistryPendingUi> = emptyList()
)

class RegistryPendingViewModel : ViewModel() {
    private val repo = AdminListingRepository(ApiClient.adminListingApi)

    private val _state = MutableStateFlow(RegistryPendingState())
    val state: StateFlow<RegistryPendingState> = _state.asStateFlow()

    fun load() = viewModelScope.launch {
        _state.value = _state.value.copy(isLoading = true, error = null)

        runCatching { repo.getRegistryPendingBookings() }
            .onSuccess { res ->
                val mapped = res.items.map { item ->
                    RegistryPendingUi(
                        bookingId = item.booking_id,
                        listingId = item.listing_id,
                        sellerName = item.seller_name,
                        sellerMobile = item.seller_mobile,
                        buyerName = item.buyer_name,
                        buyerMobile = item.buyer_mobile,
                        registryDate = item.registry_date,
                        registryTime = item.registry_time,
                        registryLocation = item.registry_location,
                        proofUrl = ApiClient.absoluteUrl(item.proof_url) ?: item.proof_url
                    )
                }
                _state.value = RegistryPendingState(
                    loaded = true,
                    isLoading = false,
                    error = null,
                    items = mapped
                )
            }
            .onFailure {
                _state.value = _state.value.copy(
                    loaded = true,
                    isLoading = false,
                    error = it.message ?: "Failed to load registry verification list"
                )
            }
    }
}
