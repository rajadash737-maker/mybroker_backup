package com.example.mybroker_admin.feature.admin.listings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.remote.dto.AdminListingItemDto
import com.example.mybroker_admin.data.repository.AdminListingRepository
import com.example.mybroker_admin.feature.admin.listings.model.AdminDocument
import com.example.mybroker_admin.feature.admin.listings.model.AdminListing
import com.example.mybroker_admin.feature.admin.listings.model.AdminListingDetail
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.text.DecimalFormat

class AdminListingsViewModel : ViewModel() {

    private val repo = AdminListingRepository(ApiClient.adminListingApi)

    private val _listings = MutableStateFlow<List<AdminListing>>(emptyList())
    val listings: StateFlow<List<AdminListing>> = _listings.asStateFlow()

    private val _detail = MutableStateFlow<AdminListingDetail?>(null)
    val detail: StateFlow<AdminListingDetail?> = _detail.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    private val _rejectReason = MutableStateFlow("")
    val rejectReason: StateFlow<String> = _rejectReason.asStateFlow()

    private val _stateFilter = MutableStateFlow("")
    val stateFilter: StateFlow<String> = _stateFilter.asStateFlow()

    private val _districtFilter = MutableStateFlow("")
    val districtFilter: StateFlow<String> = _districtFilter.asStateFlow()

    init {
        loadPendingListings()
    }

    fun onRejectReasonChange(value: String) {
        _rejectReason.value = value
    }

    fun onStateFilterChange(value: String) {
        _stateFilter.value = value
    }

    fun onDistrictFilterChange(value: String) {
        _districtFilter.value = value
    }

    fun clearFilters() {
        _stateFilter.value = ""
        _districtFilter.value = ""
        loadPendingListings()
    }

    fun applyFilters() {
        loadPendingListings(
            state = _stateFilter.value,
            district = _districtFilter.value
        )
    }

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
        return "₹ ${DecimalFormat("#,##0.##").format(value)}"
    }

    private fun mapListing(item: AdminListingItemDto): AdminListing {
        return AdminListing(
            id = item.id,
            listingCode = item.listing_code,
            sellerName = item.owner_name ?: "N/A",
            sellerMobile = item.owner_mobile ?: "N/A",
            priceText = formatPrice(item.expected_price),
            locationText = listOfNotNull(item.city, item.state).joinToString(", ").ifBlank { "N/A" },
            assignedOfficer = null,
            officerMobile = null,
            status = item.status.uppercase(),
            lockTime = null,
            lockStartedAt = null,
            lockExpiresAt = null
        )
    }

    fun loadPendingListings(
        state: String? = null,
        district: String? = null
    ) = viewModelScope.launch {
        _isLoading.value = true
        _errorMessage.value = null

        runCatching {
            repo.pendingListings(
                state = state?.takeIf { it.isNotBlank() },
                district = district?.takeIf { it.isNotBlank() }
            )
        }
            .onSuccess { dtoItems ->
                _listings.value = dtoItems.map { item -> mapListing(item) }
            }
            .onFailure { _errorMessage.value = it.message ?: "Failed to load listings" }

        _isLoading.value = false
    }

    fun loadRejectedListings(
        state: String? = null,
        district: String? = null
    ) = viewModelScope.launch {
        _isLoading.value = true
        _errorMessage.value = null

        runCatching {
            repo.rejectedListings(
                state = state?.takeIf { it.isNotBlank() },
                district = district?.takeIf { it.isNotBlank() }
            )
        }
            .onSuccess { dtoItems ->
                _listings.value = dtoItems.map { item -> mapListing(item) }
            }
            .onFailure { _errorMessage.value = it.message ?: "Failed to load rejected listings" }

        _isLoading.value = false
    }

    fun loadListingsByStatus(
        status: String,
        state: String? = null,
        district: String? = null
    ) = viewModelScope.launch {
        _isLoading.value = true
        _errorMessage.value = null

        runCatching {
            repo.getRequestsByStatus(
                status = status,
                state = state?.takeIf { it.isNotBlank() },
                district = district?.takeIf { it.isNotBlank() }
            )
        }
            .onSuccess { dtoItems ->
                _listings.value = dtoItems.map { item -> mapListing(item) }
            }
            .onFailure { _errorMessage.value = it.message ?: "Failed to load listings" }

        _isLoading.value = false
    }

    fun loadDetail(id: Int) = viewModelScope.launch {
        _isLoading.value = true
        _errorMessage.value = null

        runCatching { repo.listingDetail(id) }
            .onSuccess { d ->
                d.media.forEach { m ->
                    android.util.Log.d(
                        "DOC_DEBUG",
                        "raw media_type=${m.media_type}, doc_type=${m.document_type}, file_url=${m.file_url}"
                    )
                }

                    _detail.value = AdminListingDetail(
                        id = d.id,
                        sellerName = d.owner_name ?: "N/A",
                        sellerMobile = d.owner_mobile ?: "N/A",
                        ownershipType = sellerTypeLabel(d.ownership_type),
                        sellerCategory = sellerCategoryLabel(d.owner_category),
                        title = d.title ?: "N/A",
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
                                android.util.Log.d("DOC_DEBUG", "mapped file_url=${m.file_url}, resolved=$resolved")
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
                            .map { m ->
                                val resolved = ApiClient.absoluteUrl(m.file_url) ?: m.file_url
                                resolved
                            }
                    )
                    _rejectReason.value = d.rejection_reason ?: ""
            }
            .onFailure { _errorMessage.value = it.message ?: "Failed to load detail" }

        _isLoading.value = false
    }


    private val _actionMessage = MutableStateFlow<String?>(null)
    val actionMessage: StateFlow<String?> = _actionMessage.asStateFlow()

    fun clearActionMessage() {
        _actionMessage.value = null
    }

    fun approve(id: Int) = viewModelScope.launch {
        runCatching { repo.approve(id) }
            .onSuccess { _actionMessage.value = "Listing approved successfully" }
            .onFailure { _actionMessage.value = it.message ?: "Approval failed" }
    }

    fun reject(id: Int, reason: String) = viewModelScope.launch {
        runCatching { repo.reject(id, reason) }
            .onSuccess { _actionMessage.value = "Listing rejected successfully" }
            .onFailure { _actionMessage.value = it.message ?: "Reject failed" }
    }

    fun loadAssignmentBoard() = viewModelScope.launch {
        _isLoading.value = true
        _errorMessage.value = null

        runCatching { repo.getAssignmentBoard() }
            .onSuccess { board ->
                val locked = board.locked_cases.map { item ->
                    AdminListing(
                        id = item.id,
                        listingCode = item.listing_code,
                        sellerName = item.owner_name ?: "N/A",
                        sellerMobile = item.owner_mobile ?: "N/A",
                        priceText = "N/A",
                        locationText = item.location ?: "N/A",
                        assignedOfficer = item.assigned_field_officer?.fullname,
                        officerMobile = item.assigned_field_officer?.mobile,
                        status = "LOCKED",
                        lockTime = item.locked_for_seconds?.let { "${it / 3600} hrs ago" },
                        lockStartedAt = item.lock_started_at,
                        lockExpiresAt = item.lock_expires_at
                    )
                }

                val available = board.available_cases.map { item ->
                    AdminListing(
                        id = item.id,
                        listingCode = item.listing_code,
                        sellerName = item.owner_name ?: "N/A",
                        sellerMobile = item.owner_mobile ?: "N/A",
                        priceText = "N/A",
                        locationText = item.location ?: "N/A",
                        assignedOfficer = null,
                        officerMobile = null,
                        status = "AVAILABLE",
                        lockTime = null,
                        lockStartedAt = null,
                        lockExpiresAt = null
                    )
                }

                _listings.value = locked + available
            }
            .onFailure { _errorMessage.value = it.message ?: "Failed to load assignment board" }

        _isLoading.value = false
    }

    fun forceReleaseCase(requestId: Int) = viewModelScope.launch {
        runCatching { repo.forceReleaseCase(requestId) }
            .onSuccess {
                _actionMessage.value = "Case force released successfully"
                loadAssignmentBoard()
            }
            .onFailure {
                _actionMessage.value = it.message ?: "Force release failed"
            }
    }

    fun loadFinalApprovalCases() = viewModelScope.launch {
        _isLoading.value = true
        _errorMessage.value = null

        runCatching { repo.getFinalApprovalCases() }
            .onSuccess { res ->
                _listings.value = res.items.map { item ->
                    AdminListing(
                        id = item.id,
                        listingCode = item.listing_code,
                        sellerName = item.owner_name ?: "N/A",
                        sellerMobile = item.owner_mobile ?: "N/A",
                        priceText = "N/A",
                        locationText = item.location ?: "N/A",
                        assignedOfficer = item.field_officer?.fullname,
                        officerMobile = item.field_officer?.mobile,
                        status = "FIELD_VERIFIED",
                        lockTime = item.field_officer_reviewed_at,
                        lockStartedAt = null,
                        lockExpiresAt = null,
                        visitPhotoUrl = ApiClient.absoluteUrl(item.visit_photo_url)
                    )
                }
            }
            .onFailure { _errorMessage.value = it.message ?: "Failed to load final approval cases" }

        _isLoading.value = false
    }

    fun approveGoLive(requestId: Int) = viewModelScope.launch {
        _isLoading.value = true
        runCatching { repo.finalApprovalAction(requestId, "approve_go_live") }
            .onSuccess {
                _actionMessage.value = "Listing approved and moved to live"
                loadFinalApprovalCases()
            }
            .onFailure {
                val msg = it.message ?: "Approve & Go Live failed"
                _actionMessage.value = msg
                _errorMessage.value = msg
                _isLoading.value = false
            }
    }

    fun rejectFinal(requestId: Int, reason: String) = viewModelScope.launch {
        _isLoading.value = true
        runCatching { repo.finalApprovalAction(requestId, "reject", reason) }
            .onSuccess {
                _actionMessage.value = "Listing rejected"
                loadFinalApprovalCases()
            }
            .onFailure {
                val msg = it.message ?: "Final reject failed"
                _actionMessage.value = msg
                _errorMessage.value = msg
                _isLoading.value = false
            }
    }

    fun reassignToFieldOfficer(requestId: Int) = viewModelScope.launch {
        _isLoading.value = true
        runCatching { repo.finalApprovalAction(requestId, "reassign_to_field_officer") }
            .onSuccess {
                _actionMessage.value = "Listing reassigned to field officer"
                loadFinalApprovalCases()
            }
            .onFailure {
                val msg = it.message ?: "Reassign failed"
                _actionMessage.value = msg
                _errorMessage.value = msg
                _isLoading.value = false
            }
    }
}
