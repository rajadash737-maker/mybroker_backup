package com.example.mybroker_admin.feature.admin.listings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.repository.AdminListingRepository
import com.example.mybroker_admin.data.remote.dto.AdminFieldOfficerOptionDto
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.math.RoundingMode
import java.text.DecimalFormat
import java.text.SimpleDateFormat
import java.util.Locale

data class BookingDocumentUi(
    val name: String,
    val url: String,
    val createdAt: String? = null
)

data class BookingPartyUi(
    val name: String,
    val mobile: String?,
    val documents: List<BookingDocumentUi>
)

data class BookedLandInfoUi(
    val expectedPrice: String?,
    val dealPrice: String?,
    val location: String?
)

data class BookedPaymentInfoUi(
    val tokenAmount: String?,
    val remainingAmount: String?,
    val status: String?
)

data class RegistryInfoUi(
    val date: String?,
    val time: String?,
    val location: String?,
    val proofUrl: String?,
    val proofs: List<BookingDocumentUi>,
    val notes: String?,
    val status: String?
)

data class FieldOfficerUi(
    val id: Int,
    val name: String,
    val mobile: String?
)

data class BookedListingDetailUi(
    val bookingId: Int,
    val listingId: Int,
    val status: String,
    val bookedAt: String?,
    val bookingStatus: String,
    val buyer: BookingPartyUi,
    val seller: BookingPartyUi,
    val land: BookedLandInfoUi,
    val payment: BookedPaymentInfoUi,
    val fieldOfficer: FieldOfficerUi?,
    val registry: RegistryInfoUi?
)

data class BookedListingDetailState(
    val loaded: Boolean = false,
    val isLoading: Boolean = false,
    val error: String? = null,
    val message: String? = null,
    val detail: BookedListingDetailUi? = null,
    val fieldOfficers: List<AdminFieldOfficerOptionDto> = emptyList(),
    val isUpdatingOfficer: Boolean = false,
    val isUpdatingRegistry: Boolean = false,
    val selectedFieldOfficerId: Int? = null
)

class BookedListingDetailViewModel : ViewModel() {
    private val repo = AdminListingRepository(ApiClient.adminListingApi)

    private val _state = MutableStateFlow(BookedListingDetailState())
    val state: StateFlow<BookedListingDetailState> = _state.asStateFlow()

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

    fun load(listingId: Int) = viewModelScope.launch {
        _state.value = _state.value.copy(isLoading = true, error = null, message = null)

        runCatching { repo.getBookedListingDetail(listingId) }
            .onSuccess { dto ->
                val buyerDocs = dto.buyer.documents.mapNotNull { doc ->
                    val url = ApiClient.absoluteUrl(doc.file_url) ?: doc.file_url
                    if (url.isBlank()) null else BookingDocumentUi(doc.name, url)
                }
                val sellerDocs = dto.seller.documents.mapNotNull { doc ->
                    val url = ApiClient.absoluteUrl(doc.file_url) ?: doc.file_url
                    if (url.isBlank()) null else BookingDocumentUi(doc.name, url)
                }

                val computedDeal = dto.land.deal_price ?: run {
                    val token = dto.payment.token_amount
                    val remaining = dto.payment.remaining_amount
                    if (token != null && remaining != null) token + remaining else null
                }

                val detail = BookedListingDetailUi(
                    bookingId = dto.booking_id,
                    listingId = dto.listing_id,
                    status = dto.status.replace("_", " ").uppercase(),
                    bookedAt = formatDateTime(dto.booked_at),
                    bookingStatus = dto.booking_status.replace("_", " ").uppercase(),
                    buyer = BookingPartyUi(
                        name = dto.buyer.name,
                        mobile = dto.buyer.mobile,
                        documents = buyerDocs
                    ),
                    seller = BookingPartyUi(
                        name = dto.seller.name,
                        mobile = dto.seller.mobile,
                        documents = sellerDocs
                    ),
                    land = BookedLandInfoUi(
                        expectedPrice = formatPrice(dto.land.expected_price),
                        dealPrice = formatDealPrice(computedDeal),
                        location = dto.land.location
                    ),
                    payment = BookedPaymentInfoUi(
                        tokenAmount = formatPrice(dto.payment.token_amount),
                        remainingAmount = formatPrice(dto.payment.remaining_amount),
                        status = dto.payment.payment_status?.replace("_", " ")?.uppercase()
                    ),
                    fieldOfficer = dto.field_officer?.let {
                        FieldOfficerUi(id = it.id, name = it.fullname, mobile = it.mobile)
                    },
                    registry = dto.registry?.let { reg ->
                        val proofDocs = reg.proofs.mapNotNull { proof ->
                            val url = ApiClient.absoluteUrl(proof.file_url) ?: proof.file_url
                            if (url.isBlank()) null else BookingDocumentUi(
                                name = proof.file_name,
                                url = url,
                                createdAt = proof.created_at
                            )
                        }
                        val legacyProof = ApiClient.absoluteUrl(reg.proof_url) ?: reg.proof_url
                        val allProofs = if (!legacyProof.isNullOrBlank()) {
                            proofDocs + BookingDocumentUi("Registry Proof", legacyProof)
                        } else {
                            proofDocs
                        }
                        RegistryInfoUi(
                            date = reg.registry_date,
                            time = reg.registry_time,
                            location = reg.registry_location,
                            proofUrl = legacyProof,
                            proofs = allProofs.distinctBy { it.url },
                            notes = reg.proof_notes,
                            status = reg.status?.replace("_", " ")?.uppercase()
                        )
                    }
                )

                _state.value = _state.value.copy(
                    loaded = true,
                    isLoading = false,
                    error = null,
                    message = null,
                    detail = detail,
                    selectedFieldOfficerId = dto.field_officer?.id
                )
            }
            .onFailure {
                _state.value = _state.value.copy(
                    loaded = true,
                    isLoading = false,
                    error = it.message ?: "Failed to load booking detail",
                    message = null
                )
            }
    }

    fun loadFieldOfficers() = viewModelScope.launch {
        runCatching { repo.getFieldOfficers() }
            .onSuccess { officers ->
                _state.value = _state.value.copy(fieldOfficers = officers)
            }
            .onFailure {
                _state.value = _state.value.copy(error = it.message ?: "Failed to load field officers")
            }
    }

    fun updateFieldOfficer(bookingId: Int, officerId: Int) = viewModelScope.launch {
        _state.value = _state.value.copy(isUpdatingOfficer = true)
        runCatching { repo.updateBookingFieldOfficer(bookingId, officerId) }
            .onSuccess { res ->
                val updatedOfficer = res.field_officer
                val updatedDetail = _state.value.detail?.copy(
                    fieldOfficer = updatedOfficer?.let {
                        FieldOfficerUi(id = it.id, name = it.fullname, mobile = it.mobile)
                    }
                )
                _state.value = _state.value.copy(
                    isUpdatingOfficer = false,
                    detail = updatedDetail,
                    selectedFieldOfficerId = updatedOfficer?.id
                )
            }
            .onFailure {
                _state.value = _state.value.copy(
                    isUpdatingOfficer = false,
                    error = it.message ?: "Failed to update field officer"
                )
            }
    }

    fun scheduleRegistry(bookingId: Int, date: String, time: String, location: String) = viewModelScope.launch {
        _state.value = _state.value.copy(isUpdatingRegistry = true, message = null)
        val officerId = _state.value.selectedFieldOfficerId
        runCatching { repo.scheduleRegistry(bookingId, date, time, location, officerId) }
            .onSuccess { res ->
                val proofDocs = res.registry.proofs.mapNotNull { proof ->
                    val url = ApiClient.absoluteUrl(proof.file_url) ?: proof.file_url
                    if (url.isBlank()) null else BookingDocumentUi(
                        name = proof.file_name,
                        url = url,
                        createdAt = proof.created_at
                    )
                }
                val legacyProof = ApiClient.absoluteUrl(res.registry.proof_url) ?: res.registry.proof_url
                val allProofs = if (!legacyProof.isNullOrBlank()) {
                    proofDocs + BookingDocumentUi("Registry Proof", legacyProof)
                } else {
                    proofDocs
                }
                val updatedDetail = _state.value.detail?.copy(
                    bookingStatus = res.booking_status.replace("_", " ").uppercase(),
                    registry = RegistryInfoUi(
                        date = res.registry.registry_date,
                        time = res.registry.registry_time,
                        location = res.registry.registry_location,
                        proofUrl = legacyProof,
                        proofs = allProofs.distinctBy { it.url },
                        notes = res.registry.proof_notes,
                        status = res.registry.status?.replace("_", " ")?.uppercase()
                    )
                )
                _state.value = _state.value.copy(
                    isUpdatingRegistry = false,
                    detail = updatedDetail,
                    message = "Registry scheduled successfully"
                )
            }
            .onFailure {
                _state.value = _state.value.copy(
                    isUpdatingRegistry = false,
                    error = it.message ?: "Failed to schedule registry",
                    message = null
                )
            }
    }

    fun verifyRegistry(bookingId: Int, decision: String) = viewModelScope.launch {
        _state.value = _state.value.copy(isUpdatingRegistry = true)
        runCatching { repo.verifyRegistry(bookingId, decision) }
            .onSuccess { res ->
                val updatedDetail = _state.value.detail?.copy(
                    bookingStatus = res.booking_status.replace("_", " ").uppercase(),
                    registry = _state.value.detail?.registry?.copy(
                        status = res.booking_status.replace("_", " ").uppercase()
                    )
                )
                _state.value = _state.value.copy(
                    isUpdatingRegistry = false,
                    detail = updatedDetail
                )
            }
            .onFailure {
                _state.value = _state.value.copy(
                    isUpdatingRegistry = false,
                    error = it.message ?: "Failed to verify registry"
                )
            }
    }
}
