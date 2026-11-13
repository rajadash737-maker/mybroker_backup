package com.example.mybroker_admin.feature.admin.approvals.model

data class FinalApprovalListing(
    val id: Int,
    val sellerName: String,
    val sellerMobile: String,
    val location: String,
    val officerName: String,
    val officerMobile: String,
    val visitDate: String,
    val recommendation: String, // APPROVE / REJECT
    val reportSummary: String,
    val fieldPhotos: List<String>
)