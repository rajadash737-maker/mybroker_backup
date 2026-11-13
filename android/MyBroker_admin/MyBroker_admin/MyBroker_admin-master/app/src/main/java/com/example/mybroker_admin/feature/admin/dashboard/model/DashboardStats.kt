package com.example.mybroker_admin.feature.admin.dashboard.model

data class DashboardStats(
    val pendingCount: Int = 0,
    val assignedCount: Int = 0,
    val fieldVerifiedCount: Int = 0,
    val liveCount: Int = 0,
    val lockedCount: Int = 0,
    val bookedCount: Int = 0,
    val soldCount: Int = 0,
    val rejectedCount: Int = 0,
    val adminName: String = "Admin",
    val profileImageUrl: String? = null,
    val cancelPendingCount: Int = 0,
    val refundSuccessCount: Int = 0,
    val pendingRegistryVerificationCount: Int = 0
)
