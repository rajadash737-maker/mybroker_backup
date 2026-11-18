package com.example.myapplication.ui.feature.sitevisit.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.myapplication.ui.feature.sitevisit.data.SiteVisitBookingDto
import com.example.myapplication.ui.feature.sitevisit.data.SiteVisitCancelRequest
import com.example.myapplication.ui.feature.sitevisit.data.SiteVisitCancelResponse
import com.example.myapplication.ui.feature.sitevisit.data.SiteVisitCreateRequest
import com.example.myapplication.ui.feature.sitevisit.data.SiteVisitOrderDto
import com.example.myapplication.ui.feature.sitevisit.data.SiteVisitRepository
import com.example.myapplication.ui.feature.sitevisit.data.SiteVisitVerifyPaymentRequest
import com.example.myapplication.ui.feature.sitevisit.data.SiteVisitCorrectionResponseRequest
import com.example.myapplication.ui.feature.sitevisit.data.SiteVisitRefundDetailsRequest
import java.util.UUID
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class SiteVisitUiState(
    val loading: Boolean = false,
    val submitting: Boolean = false,
    val feeRupees: String? = null,
    val bookings: List<SiteVisitBookingDto> = emptyList(),
    val listingLookupLoading: Boolean = false,
    val listingLookupComplete: Boolean = false,
    val listingLookupError: String? = null,
    val existingBooking: SiteVisitBookingDto? = null,
    val booking: SiteVisitBookingDto? = null,
    val bookingId: Int? = null,
    val order: SiteVisitOrderDto? = null,
    val checkoutInProgress: Boolean = false,
    val message: String? = null,
    val error: String? = null,
    val canceling: Boolean = false,
    val cancelResponse: SiteVisitCancelResponse? = null
)

class SiteVisitViewModel : ViewModel() {
    private val repository = SiteVisitRepository()
    private val _state = MutableStateFlow(SiteVisitUiState())
    val state: StateFlow<SiteVisitUiState> = _state
    private var submissionKey = UUID.randomUUID().toString()
    private var lookupListingId: Int? = null
    private var orderRequestInFlight = false

    fun load(listingId: Int? = null) {
        lookupListingId = listingId?.takeIf { it > 0 }
        if (lookupListingId != null) {
            _state.value = _state.value.copy(
                listingLookupLoading = true,
                listingLookupComplete = false,
                listingLookupError = null,
                existingBooking = null,
                error = null
            )
        }
        viewModelScope.launch {
            runCatching { repository.fee() }.onSuccess {
                _state.value = _state.value.copy(feeRupees = it.rupees)
            }.onFailure {
                _state.value = _state.value.copy(error = "Could not load Site Visit fee. Check your connection and retry.")
            }
        }
        refresh()
    }

    fun refresh() = viewModelScope.launch {
        _state.value = _state.value.copy(loading = true, error = null)
        runCatching { repository.bookings() }.onSuccess {
            val current = _state.value
            _state.value = current.copy(
                bookings = it,
                booking = current.booking?.let { saved -> it.firstOrNull { updated -> updated.id == saved.id } ?: saved },
                loading = false,
                listingLookupLoading = false,
                listingLookupComplete = lookupListingId != null || current.listingLookupComplete,
                listingLookupError = null,
                existingBooking = lookupListingId?.let { id -> SiteVisitUiRules.existingBookingForListing(it, id) }
            )
        }.onFailure {
            val failure = "Could not check existing Site Visits for this listing. Retry before creating a booking."
            _state.value = _state.value.copy(
                loading = false,
                listingLookupLoading = false,
                listingLookupError = if (lookupListingId != null) failure else null,
                error = if (lookupListingId != null) failure else "Could not refresh your bookings. Check your connection and retry."
            )
        }
    }

    fun submit(listingId: Int, date: String, time: String, visitors: String, address: String, message: String) = viewModelScope.launch {
        val current = _state.value
        if (!SiteVisitUiRules.canCreateForListing(
                current.listingLookupComplete,
                current.listingLookupError != null,
                current.existingBooking
            ) || lookupListingId != listingId
        ) {
            _state.value = current.copy(error = "Existing bookings must be checked before submitting a new request.")
            return@launch
        }
        val count = visitors.toIntOrNull()
        val parts = time.split(":")
        val dateTimeError = SiteVisitBookingTime.validate(
            date, parts.getOrNull(0), parts.getOrNull(1), java.time.LocalDate.now(), java.time.LocalTime.now()
        )
        if (dateTimeError != null || count == null || count !in 1..20 || address.trim().length !in 10..1000) {
            _state.value = _state.value.copy(error = dateTimeError ?: "Enter 1–20 visitors and a pickup address between 10 and 1000 characters.")
            return@launch
        }
        _state.value = _state.value.copy(submitting = true, error = null, message = null)
        runCatching {
            repository.create(SiteVisitCreateRequest(listingId, date, time, count!!, address.trim(), message.trim().ifBlank { null }, submissionKey))
        }.onSuccess { booking ->
            _state.value = _state.value.copy(
                submitting = false,
                bookingId = booking.id,
                booking = booking,
                message = null,
                error = null
            )
            submissionKey = UUID.randomUUID().toString()
            refresh()
        }.onFailure { error ->
            _state.value = _state.value.copy(
                submitting = false,
                error = SiteVisitApiErrorMessage.from(error)
            )
        }
    }

    fun cancelBooking(booking: SiteVisitBookingDto, reason: String, upiId: String) = viewModelScope.launch {
        val normalizedReason = reason.trim()
        val needsRefundDetails = SiteVisitUiRules.requiresRefundUpiBeforeCancellation(booking)
        val normalizedUpiId = upiId.trim()
        if (normalizedReason.length !in 3..500) {
            _state.value = _state.value.copy(error = "Enter a cancellation reason between 3 and 500 characters.")
            return@launch
        }
        if (needsRefundDetails && !SiteVisitUiRules.isValidUpiId(normalizedUpiId)) {
            _state.value = _state.value.copy(error = "Enter a valid UPI ID for refund processing.")
            return@launch
        }
        _state.value = _state.value.copy(canceling = true, error = null, message = null, cancelResponse = null)
        runCatching { repository.cancel(booking.id, SiteVisitCancelRequest(normalizedReason)) }
            .onSuccess { response ->
                // The backend creates a refund case during cancellation, so accepted UPI details
                // must be submitted afterward. A failed second call leaves the case recoverable
                // from My Site Visits in its pending_details state.
                val refundSubmission = if (needsRefundDetails) {
                    runCatching {
                        repository.submitRefundDetails(booking.id, SiteVisitRefundDetailsRequest(normalizedUpiId))
                    }
                } else null
                val refundSubmissionError = refundSubmission?.exceptionOrNull()?.let { SiteVisitApiErrorMessage.refundDetails(it) }
                _state.value = _state.value.copy(
                    canceling = false,
                    cancelResponse = response,
                    message = when {
                        refundSubmission?.isSuccess == true -> "Booking cancelled. Refund details were submitted for Accounting review."
                        refundSubmissionError != null -> "Booking cancelled. $refundSubmissionError"
                        needsRefundDetails -> "Booking cancelled. Refund details are still needed; submit them from this booking in My Site Visits."
                        else -> response.status
                    },
                    error = null
                )
                refresh()
            }
            .onFailure {
                _state.value = _state.value.copy(
                    canceling = false,
                    error = "The server could not cancel this Site Visit. Refresh status and retry if it is still eligible."
                )
            }
    }

    fun resubmitCorrection(bookingId: Int, date: String, time: String, visitors: String, address: String, message: String) = viewModelScope.launch {
        val count = visitors.toIntOrNull()
        if (runCatching { java.time.LocalDate.parse(date) }.isFailure || runCatching { java.time.LocalTime.parse(time) }.isFailure ||
            count == null || count !in 1..20 || address.trim().length !in 10..1000 || message.length > 2000
        ) {
            _state.value = _state.value.copy(error = "Enter a valid visit date and time, 1–20 visitors, and a pickup address between 10 and 1000 characters.")
            return@launch
        }
        _state.value = _state.value.copy(submitting = true, error = null, message = null)
        runCatching {
            repository.resubmitCorrection(bookingId, SiteVisitCorrectionResponseRequest(date, time, count!!, address.trim(), message.trim().ifBlank { null }))
        }.onSuccess {
            _state.value = _state.value.copy(submitting = false, message = "Corrected details sent for admin review.")
            refresh()
        }.onFailure {
            _state.value = _state.value.copy(submitting = false, error = "Correction could not be resubmitted. Refresh status and verify that the booking still requires correction.")
        }
    }

    fun submitRefundDetails(bookingId: Int, upiId: String) = viewModelScope.launch {
        val normalized = upiId.trim()
        if (!Regex("^[A-Za-z0-9._-]{2,80}@[A-Za-z0-9.-]{2,40}$").matches(normalized)) {
            _state.value = _state.value.copy(error = "Enter a valid UPI ID.")
            return@launch
        }
        _state.value = _state.value.copy(submitting = true, error = null, message = null)
        runCatching { repository.submitRefundDetails(bookingId, SiteVisitRefundDetailsRequest(normalized)) }
            .onSuccess {
                _state.value = _state.value.copy(submitting = false, message = "Refund details were securely submitted.")
                refresh()
            }
            .onFailure { error ->
                _state.value = _state.value.copy(submitting = false, error = SiteVisitApiErrorMessage.refundDetails(error))
            }
    }

    fun createOrder(bookingId: Int) {
        val current = _state.value
        if (orderRequestInFlight || current.submitting || current.checkoutInProgress || current.order != null) return
        orderRequestInFlight = true
        _state.value = current.copy(submitting = true, bookingId = bookingId, error = null, message = null)
        viewModelScope.launch {
            runCatching { repository.order(bookingId) }.onSuccess {
                _state.value = _state.value.copy(submitting = false, bookingId = bookingId, order = it)
            }.onFailure {
                _state.value = _state.value.copy(submitting = false, error = "Payment order could not be created. Refresh and retry.")
            }
            orderRequestInFlight = false
        }
    }

    fun paymentSuccess(paymentId: String?, orderId: String?, signature: String?) = viewModelScope.launch {
        val bookingId = _state.value.bookingId ?: return@launch
        if (paymentId.isNullOrBlank() || orderId.isNullOrBlank() || signature.isNullOrBlank()) {
            _state.value = _state.value.copy(error = "Payment callback was incomplete. Refresh booking status before retrying.")
            refresh()
            return@launch
        }
        _state.value = _state.value.copy(submitting = true, checkoutInProgress = false, order = null, error = null)
        runCatching { repository.verify(bookingId, SiteVisitVerifyPaymentRequest(orderId, paymentId, signature)) }
            .onSuccess {
                _state.value = _state.value.copy(submitting = false, message = "Payment verified by MyBrokerr.")
                refresh()
            }.onFailure {
                _state.value = _state.value.copy(submitting = false, error = "Payment verification is pending. Refresh status before attempting another payment.")
                refresh()
            }
    }

    fun paymentFailure() = viewModelScope.launch {
        val bookingId = _state.value.bookingId ?: return@launch
        _state.value = _state.value.copy(order = null, checkoutInProgress = false, error = "Checkout was not completed. You can retry payment.")
        runCatching { repository.cancelPayment(bookingId) }
        refresh()
    }

    fun checkoutLaunched() { _state.value = _state.value.copy(order = null, checkoutInProgress = true) }

    fun clearMessages() { _state.value = _state.value.copy(message = null, error = null) }
}
