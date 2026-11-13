package com.example.mybroker_admin.feature.superadmin.listings.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.repository.AdminListingRepository
import com.example.mybroker_admin.feature.admin.listings.BookedLandInfoUi
import com.example.mybroker_admin.feature.admin.listings.BookedListingDetailUi
import com.example.mybroker_admin.feature.admin.listings.BookedPaymentInfoUi
import com.example.mybroker_admin.feature.admin.listings.BookingDocumentUi
import com.example.mybroker_admin.feature.admin.listings.BookingPartyUi
import com.example.mybroker_admin.feature.admin.listings.FieldOfficerUi
import com.example.mybroker_admin.feature.admin.listings.RegistryInfoUi
import com.example.mybroker_admin.feature.admin.listings.model.AdminDocument
import com.example.mybroker_admin.feature.admin.listings.model.AdminListingDetail
import com.example.mybroker_admin.feature.superadmin.listings.model.SuperAdminListingDetailState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.text.DecimalFormat

class SuperAdminListingDetailViewModel : ViewModel() {

    private val repo = AdminListingRepository(ApiClient.adminListingApi)

    private val _state = MutableStateFlow(SuperAdminListingDetailState())
    val state: StateFlow<SuperAdminListingDetailState> = _state

    private val _detail = MutableStateFlow<AdminListingDetail?>(null)
    val detail: StateFlow<AdminListingDetail?> = _detail

    private val _bookedDetail = MutableStateFlow<BookedListingDetailUi?>(null)
    val bookedDetail: StateFlow<BookedListingDetailUi?> = _bookedDetail

    private val _bookingError = MutableStateFlow<String?>(null)
    val bookingError: StateFlow<String?> = _bookingError

    private fun sellerTypeLabel(raw: String?): String = when (raw?.trim()?.lowercase()) {
        "single_owner" -> "Single Owner"
        "multi_owner" -> "Multi Owner"
        "inherited_land" -> "Inherited Land"
        "owner" -> "Single Owner"
        "broker" -> "Multi Owner"
        "power_of_attorney" -> "Inherited Land"
        else -> raw?.replace("_", " ")?.replaceFirstChar { it.uppercase() } ?: "N/A"
    }

    private fun sellerCategoryLabel(raw: String?): String = when (raw?.trim()?.lowercase()) {
        "general" -> "General"
        "obc" -> "OBC"
        "sc" -> "SC"
        "st" -> "ST"
        else -> raw?.replace("_", " ")?.replaceFirstChar { it.uppercase() } ?: "N/A"
    }

    private fun formatPrice(value: Double?): String {
        if (value == null || value <= 0.0) return "N/A"
        return "Rs. ${DecimalFormat("#,##0.##").format(value)}"
    }

    fun loadDetail(id: Int) {
        _state.update { it.copy(isLoading = true, error = null) }
        _bookedDetail.value = null
        _bookingError.value = null
        viewModelScope.launch {
            runCatching { repo.listingDetail(id) }
                .onSuccess { d ->
                    _detail.value = AdminListingDetail(
                        id = d.id,
                        sellerName = d.owner_name ?: "N/A",
                        sellerMobile = d.owner_mobile ?: "N/A",
                        ownershipType = sellerTypeLabel(d.ownership_type),
                        sellerCategory = sellerCategoryLabel(d.owner_category),
                        title = d.title ?: "N/A",
                        instagramUrl = d.instagram_url,
                        landType = d.land_type?.replaceFirstChar { it.uppercase() } ?: "N/A",
                        area = if (d.area != null) "${d.area} ${d.area_unit ?: ""}".trim() else "N/A",
                        city = d.city ?: "N/A",
                        state = d.state ?: "N/A",
                        pincode = d.pincode ?: "N/A",
                        priceType = d.price_type?.replace("_", " ")?.replaceFirstChar { it.uppercase() } ?: "Total Price",
                        expectedPrice = formatPrice(d.expected_price),
                        negotiable = d.negotiable,
                        documents = d.media
                            .filter { it.media_type.equals("document", ignoreCase = true) }
                            .map { m ->
                                val resolved = ApiClient.absoluteUrl(m.file_url) ?: m.file_url
                                AdminDocument(
                                    name = m.document_type ?: "document",
                                    url = resolved
                                )
                            },
                        status = d.status.replace("_", " ").uppercase(),
                        rejectionReason = d.rejection_reason,
                        reviewedById = d.reviewed_by_id,
                        reviewedAt = d.reviewed_at,
                        submittedAt = d.created_at,
                        paymentStatus = d.payment_status,
                        paymentPaidAt = d.payment_paid_at,
                        paymentAmount = formatPrice(d.payment_amount),
                        adminHandlerName = d.admin_handler?.fullname,
                        adminHandlerMobile = d.admin_handler?.mobile,
                        fieldOfficerName = d.field_officer?.fullname,
                        fieldOfficerMobile = d.field_officer?.mobile,
                        cancellationReason = d.cancellation_reason,
                        refundUpiId = d.refund_upi_id,
                        refundAmount = formatPrice(d.refund_amount),
                        refundTxnId = d.refund_transaction_id,
                        refundCompletedAt = d.refund_completed_at,
                        photos = d.media
                            .filter { it.media_type.equals("photo", ignoreCase = true) }
                            .map { m -> ApiClient.absoluteUrl(m.file_url) ?: m.file_url }
                    )
                    _state.update { it.copy(instagramInput = d.instagram_url.orEmpty(), instagramError = null) }
                    _state.update { it.copy(isLoading = false) }

                    val status = d.status.uppercase()
                    if (status == "BOOKED" || status == "SOLD") {
                        loadBookedDetail(id)
                    }
                }
                .onFailure { err ->
                    _state.update { it.copy(isLoading = false, error = err.message ?: "Failed to load detail") }
                }
        }
    }

    fun onInstagramInputChange(value: String) {
        _state.update { it.copy(instagramInput = value, instagramError = null, instagramMessage = null) }
    }

    fun saveInstagramUrl(listingId: Int) {
        val value = _state.value.instagramInput.trim()
        if (value.isEmpty()) {
            _state.update { it.copy(instagramError = "Enter an Instagram URL, or use Remove to clear it.") }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(instagramSaving = true, instagramError = null, instagramMessage = null) }
            runCatching { repo.updateListingInstagramUrl(listingId, value) }
                .onSuccess {
                    _state.update { it.copy(instagramSaving = false, instagramMessage = "Instagram URL saved.") }
                    loadDetail(listingId)
                }
                .onFailure { error ->
                    _state.update { it.copy(instagramSaving = false, instagramError = error.message ?: "Unable to save Instagram URL.") }
                }
        }
    }

    fun removeInstagramUrl(listingId: Int) {
        viewModelScope.launch {
            _state.update { it.copy(instagramSaving = true, instagramError = null, instagramMessage = null) }
            runCatching { repo.updateListingInstagramUrl(listingId, null) }
                .onSuccess {
                    _state.update { it.copy(instagramSaving = false, instagramMessage = "Instagram URL removed.", instagramInput = "") }
                    loadDetail(listingId)
                }
                .onFailure { error ->
                    _state.update { it.copy(instagramSaving = false, instagramError = error.message ?: "Unable to remove Instagram URL.") }
                }
        }
    }

    private fun loadBookedDetail(listingId: Int) {
        viewModelScope.launch {
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
                    val registry = dto.registry?.let { reg ->
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

                    _bookedDetail.value = BookedListingDetailUi(
                        bookingId = dto.booking_id,
                        listingId = dto.listing_id,
                        status = dto.status.replace("_", " ").uppercase(),
                        bookedAt = dto.booked_at,
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
                            dealPrice = formatPrice(dto.land.deal_price),
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
                        registry = registry
                    )
                }
                .onFailure { err ->
                    _bookingError.value = err.message ?: "Failed to load booking detail"
                }
        }
    }
}
