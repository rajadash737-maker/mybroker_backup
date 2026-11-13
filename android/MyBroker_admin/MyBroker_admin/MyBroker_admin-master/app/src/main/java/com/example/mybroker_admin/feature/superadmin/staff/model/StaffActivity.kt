package com.example.mybroker_admin.feature.superadmin.staff.model

data class StaffActivity(
    val id: String,
    val staffId: String,
    val action: String,
    val targetId: String?,
    val timestamp: Long
)
