package com.example.mybroker_admin.feature.admin.cancel.presentation.state

import com.example.mybroker_admin.feature.admin.cancel.viewmodel.RefundUiModel

enum class RefundTab {
    PENDING,
    SUCCESS
}

data class CancelRefundState(
    val selectedTab: RefundTab = RefundTab.PENDING,
    val pendingList: List<RefundUiModel> = emptyList(),
    val successList: List<RefundUiModel> = emptyList(),
    val isLoading: Boolean = false,
    val isForwarding: Boolean = false,
    val errorMessage: String? = null,
    val successMessage: String? = null
)
