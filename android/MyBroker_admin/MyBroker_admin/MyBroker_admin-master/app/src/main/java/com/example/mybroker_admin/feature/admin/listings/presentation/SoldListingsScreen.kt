package com.example.mybroker_admin.feature.admin.listings.presentation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.mybroker_admin.feature.admin.listings.SoldListingsViewModel

@Composable
fun SoldListingsRoute(
    onListingClick: (Int) -> Unit = {},
    onBack: () -> Unit = {}
) {
    val vm: SoldListingsViewModel = viewModel()
    val state = vm.state.collectAsState().value

    LaunchedEffect(Unit) {
        if (!state.loaded) vm.load()
    }

    BookedListingsScreen(
        state = state,
        onRetry = vm::load,
        onListingClick = onListingClick,
        onBack = onBack,
        title = "Sold Listings"
    )
}
