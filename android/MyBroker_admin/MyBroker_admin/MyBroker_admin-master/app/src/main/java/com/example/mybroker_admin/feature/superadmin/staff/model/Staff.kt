package com.example.mybroker_admin.feature.superadmin.staff.model



import com.example.mybroker_admin.core.model.UserRole

data class Staff(
    val id: String,
    val name: String,
    val email: String,
    val role: UserRole,
    val active: Boolean = true,

    // Performance tracking
    val todayWorkCount: Int = 0,
    val totalActions: Int = 0,
    val revenueGenerated: Double = 0.0,

    // Tracking
    val lastActiveAt: Long? = null,
    val createdAt: Long? = null
)
