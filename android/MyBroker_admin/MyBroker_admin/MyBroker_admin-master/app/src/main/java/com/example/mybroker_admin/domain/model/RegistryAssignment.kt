package com.example.mybroker_admin.domain.model

data class RegistryAssignment(
    val id: String,
    val listingId: Int? = null,
    val dealAmount: Double? = null,
    val propertyName: String,
    val propertyType: String,
    val propertyArea: String,
    val propertyAddress: String,
    val buyerName: String,
    val sellerName: String,
    val buyerPhone: String,
    val sellerPhone: String,
    val date: String,
    val time: String,
    val location: String,
    val status: RegistryStatus,
    val assignedOfficer: String,
    val proofUrls: List<String> = emptyList()
)
