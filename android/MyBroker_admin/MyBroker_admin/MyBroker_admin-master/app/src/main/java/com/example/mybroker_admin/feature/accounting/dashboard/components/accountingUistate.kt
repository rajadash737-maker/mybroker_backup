package com.example.mybroker_admin.feature.accounting.dashboard.components

enum class AccountingRevenueRangeType(val value: String) {
    ALL("all"),
    TODAY("today"),
    WEEK("week"),
    MONTH("month"),
    CUSTOM("custom")
}

data class AccountingDashboardState(
    val totalRevenue: Double = 0.0,
    val pendingPayments: Int = 0,
    val completedTransactions: Int = 0,
    val accountantName: String = "Accounting",
    val profileImageUrl: String? = null,
    val pendingRefunds: Int = 0,
    val webhookLogCount: Int = 0,
    val rangeType: AccountingRevenueRangeType = AccountingRevenueRangeType.MONTH,
    val customStart: String = "",
    val customEnd: String = "",
    val isLoading: Boolean = false,
    val errorMessage: String? = null
)
