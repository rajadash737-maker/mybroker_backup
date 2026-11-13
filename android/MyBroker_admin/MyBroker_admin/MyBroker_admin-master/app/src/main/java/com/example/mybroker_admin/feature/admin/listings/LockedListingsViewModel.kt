package com.example.mybroker_admin.feature.admin.listings



import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.repository.AdminListingRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.text.DecimalFormat

data class LockedListingUi(
    val id: Int,
    val listingCode: String?,
    val sellerName: String,
    val sellerMobile: String?,
    val buyerName: String?,
    val buyerMobile: String?,
    val expectedPrice: String?,
    val dealPrice: String?,
    val lockedForSeconds: Int?
)

data class LockedListingsState(
    val loaded: Boolean = false,
    val isLoading: Boolean = false,
    val error: String? = null,
    val items: List<LockedListingUi> = emptyList()
)

class LockedListingsViewModel : ViewModel() {
    private val repo = AdminListingRepository(ApiClient.adminListingApi)

    private val _state = MutableStateFlow(LockedListingsState())
    val state: StateFlow<LockedListingsState> = _state.asStateFlow()

    private fun formatPrice(value: Double?): String? {
        if (value == null || value <= 0.0) return null
        return "₹ ${DecimalFormat("#,##0.##").format(value)}"
    }

    fun load() = viewModelScope.launch {
        _state.value = _state.value.copy(isLoading = true, error = null)

        runCatching { repo.getLockedListings() }
            .onSuccess { res ->
                val mapped = res.items.map { item ->
                    LockedListingUi(
                        id = item.id,
                        listingCode = item.listing_code,
                        sellerName = item.seller.fullname,
                        sellerMobile = item.seller.mobile,
                        buyerName = item.buyer?.fullname,
                        buyerMobile = item.buyer?.mobile,
                        expectedPrice = formatPrice(item.expected_price),
                        dealPrice = formatPrice(item.deal_price),
                        lockedForSeconds = item.locked_for_seconds
                    )
                }
                _state.value = LockedListingsState(
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
                    error = it.message ?: "Failed to load locked listings"
                )
            }
    }

    fun forceRelease(requestId: Int) = viewModelScope.launch {
        runCatching { repo.forceReleaseOfferLock(requestId) }
            .onSuccess {
                load()
            }
            .onFailure {
                _state.value = _state.value.copy(error = it.message ?: "Force release failed")
            }
    }
}
