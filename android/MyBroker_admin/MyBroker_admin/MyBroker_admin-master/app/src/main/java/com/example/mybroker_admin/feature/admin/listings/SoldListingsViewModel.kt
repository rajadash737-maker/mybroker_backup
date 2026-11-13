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

class  SoldListingsViewModel : ViewModel() {
    private val repo = AdminListingRepository(ApiClient.adminListingApi)

    private val _state = MutableStateFlow(BookedListingsState())
    val state: StateFlow<BookedListingsState> = _state.asStateFlow()

    private fun formatPrice(value: Double?): String? {
        if (value == null || value <= 0.0) return null
        return "\u20B9 ${DecimalFormat("#,##0.##").format(value)}"
    }

    fun load() = viewModelScope.launch {
        _state.value = _state.value.copy(isLoading = true, error = null)

        runCatching { repo.getSoldListings() }
            .onSuccess { res ->
                val mapped = res.items.map { item ->
                    BookedListingUi(
                        id = item.id,
                        listingCode = item.listing_code,
                        sellerName = item.seller.fullname,
                        sellerMobile = item.seller.mobile,
                        buyerName = item.buyer?.fullname,
                        buyerMobile = item.buyer?.mobile,
                        fieldOfficerName = item.field_officer?.fullname,
                        fieldOfficerMobile = item.field_officer?.mobile,
                        expectedPrice = formatPrice(item.expected_price),
                        dealPrice = formatPrice(item.deal_price),
                        bookingFee = formatPrice(item.booking_fee_amount),
                        paymentStatus = item.payment_status?.replace("_", " ")?.uppercase(),
                        bookingStatus = item.booking_status?.replace("_", " ")?.uppercase(),
                        bookedAt = item.booked_at
                    )
                }
                _state.value = BookedListingsState(
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
                    error = it.message ?: "Failed to load sold listings"
                )
            }
    }
}
