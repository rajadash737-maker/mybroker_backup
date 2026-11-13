package com.example.mybroker_admin.feature.admin.listings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.repository.AdminListingRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.math.RoundingMode
import java.text.DecimalFormat
import java.text.SimpleDateFormat
import java.util.Locale

data class BookedListingUi(
    val id: Int,
    val listingCode: String?,
    val sellerName: String,
    val sellerMobile: String?,
    val buyerName: String?,
    val buyerMobile: String?,
    val fieldOfficerName: String?,
    val fieldOfficerMobile: String?,
    val expectedPrice: String?,
    val dealPrice: String?,
    val bookingFee: String?,
    val paymentStatus: String?,
    val bookingStatus: String?,
    val bookedAt: String?
)

data class BookedListingsState(
    val loaded: Boolean = false,
    val isLoading: Boolean = false,
    val error: String? = null,
    val items: List<BookedListingUi> = emptyList()
)

class BookedListingsViewModel : ViewModel() {
    private val repo = AdminListingRepository(ApiClient.adminListingApi)

    private val _state = MutableStateFlow(BookedListingsState())
    val state: StateFlow<BookedListingsState> = _state.asStateFlow()

    private fun formatPrice(value: Double?): String? {
        if (value == null || value <= 0.0) return null
        return "\u20B9 ${DecimalFormat("#,##0.##").format(value)}"
    }

    private fun formatDealPrice(value: Double?): String? {
        if (value == null || value <= 0.0) return null
        val formatter = DecimalFormat("#,##0").apply { roundingMode = RoundingMode.DOWN }
        return "\u20B9 ${formatter.format(value)}"
    }

    private fun formatDateTime(raw: String?): String? {
        if (raw.isNullOrBlank()) return null
        val cleaned = raw.trim()
            .replace("Z", "")
            .replace(Regex("[+-]\\d{2}:?\\d{2}$"), "")
            .let { value ->
                val dot = value.indexOf(".")
                if (dot >= 0) value.substring(0, dot) else value
            }

        val inputFormats = listOf(
            SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.ENGLISH),
            SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.ENGLISH)
        )
        val output = SimpleDateFormat("dd MMMM yyyy, hh.mm a", Locale.ENGLISH)

        for (fmt in inputFormats) {
            runCatching {
                val date = fmt.parse(cleaned) ?: return@runCatching null
                return output.format(date).replace("AM", "am").replace("PM", "pm")
            }
        }
        return raw
    }

    fun load() = viewModelScope.launch {
        _state.value = _state.value.copy(isLoading = true, error = null)

        runCatching { repo.getBookedListings() }
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
                        dealPrice = formatDealPrice(item.deal_price),
                        bookingFee = formatPrice(item.booking_fee_amount),
                        paymentStatus = item.payment_status?.replace("_", " ")?.uppercase(),
                        bookingStatus = item.booking_status?.replace("_", " ")?.uppercase(),
                        bookedAt = formatDateTime(item.booked_at)
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
                    error = it.message ?: "Failed to load booked listings"
                )
            }
    }
}
