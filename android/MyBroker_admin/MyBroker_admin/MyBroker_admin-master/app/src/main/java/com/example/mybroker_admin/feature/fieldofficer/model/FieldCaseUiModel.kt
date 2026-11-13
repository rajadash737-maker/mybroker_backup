package com.example.mybroker_admin.feature.fieldofficer.model

import com.google.android.gms.maps.model.LatLng

enum class FieldStatus {
    AVAILABLE,
    LOCKED,
    APPROVED,
    REJECTED
}

data class FieldCaseUiModel(
    val id: String,
    val sellerName: String,
    val districtState: String = "-",
    val pincode: String = "-",
    val status: FieldStatus,
    val isLocked: Boolean = false,
    val lockExpiryTime: Long? = null,
    val rejectReason: String? = null,
    val latitude: Double = 0.0,
    val longitude: Double = 0.0,
    val polygonPoints: List<LatLng> = emptyList()
)


