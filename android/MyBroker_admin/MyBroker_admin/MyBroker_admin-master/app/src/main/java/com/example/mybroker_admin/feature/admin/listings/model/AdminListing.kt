package com.example.mybroker_admin.feature.admin.listings.model




data class AdminListing(
    val id: Int,
    val listingCode: String? = null,
    val sellerName: String,
    val sellerMobile: String,
    val priceText: String = "N/A",
    val locationText: String,
    val assignedOfficer: String? = null,
    val officerMobile: String? = null,
    val status: String, // "LOCKED" or "AVAILABLE"
    val lockTime: String? = null,
    val lockStartedAt: String? = null,
    val lockExpiresAt: String? = null,
    val visitPhotoUrl: String? = null

)



data class AdminDocument(
    val name: String,
    val url: String
)

data class AdminListingDetail(
    val id: Int,
    val sellerName: String,
    val sellerMobile: String,
    val ownershipType: String,
    val sellerCategory: String,
    val title: String,
    val landType: String,
    val area: String,
    val city: String,
    val state: String,
    val pincode: String,
    val priceType: String,
    val expectedPrice: String,
    val negotiable: Boolean,
    val documents: List<AdminDocument>,
    val status: String = "N/A",
    val rejectionReason: String? = null,
    val reviewedById: Int? = null,
    val reviewedAt: String? = null,
    val submittedAt: String? = null,
    val paymentStatus: String? = null,
    val paymentPaidAt: String? = null,
    val paymentAmount: String? = null,
    val adminHandlerName: String? = null,
    val adminHandlerMobile: String? = null,
    val fieldOfficerName: String? = null,
    val fieldOfficerMobile: String? = null,
    val cancellationReason: String? = null,
    val refundUpiId: String? = null,
    val refundAmount: String? = null,
    val refundTxnId: String? = null,
    val refundCompletedAt: String? = null,
    val photos: List<String> = emptyList(),
    val instagramUrl: String? = null
)

