package com.example.mybroker_admin.feature.admin.cancel.presentation.components



import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import com.example.mybroker_admin.feature.admin.cancel.presentation.state.RefundTab

@Composable
fun CancelTabRow(
    selectedTab: RefundTab,
    onTabSelected: (RefundTab) -> Unit
) {

    val tabs = listOf(RefundTab.PENDING, RefundTab.SUCCESS)

    TabRow(
        selectedTabIndex = tabs.indexOf(selectedTab)
    ) {
        tabs.forEach { tab ->
            Tab(
                selected = selectedTab == tab,
                onClick = { onTabSelected(tab) },
                text = {
                    Text(
                        text = when (tab) {
                            RefundTab.PENDING -> "Pending Refund"
                            RefundTab.SUCCESS -> "Successful Refund"
                        }
                    )
                }
            )
        }
    }
}