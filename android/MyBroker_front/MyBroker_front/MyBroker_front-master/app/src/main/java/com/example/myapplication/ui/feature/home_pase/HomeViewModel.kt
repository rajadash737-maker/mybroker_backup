package com.example.myapplication.ui.feature.home_pase

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.myapplication.network.ApiService
import com.example.myapplication.network.BannerResponse
import com.example.myapplication.network.ConnectivityObserver
import com.example.myapplication.ui.feature.buyer.domain.repository.LandRepository
import com.example.myapplication.ui.feature.home_pase.components.HomeLandItem
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class HomeUiState(
    val userName: String = "User",
    val banners: List<BannerResponse> = emptyList(),
    val nearbyLands: List<HomeLandItem> = emptyList(),
    val isConnected: Boolean = true,
    val isRefreshing: Boolean = false
)

sealed interface HomeEvent {
    data object OnRetry : HomeEvent
    data object OnRefresh : HomeEvent
}

class HomeViewModel(
    private val api: ApiService,
    private val landRepository: LandRepository,
    connectivityObserver: ConnectivityObserver
) : ViewModel() {
    private val _uiState = MutableStateFlow(HomeUiState())
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            connectivityObserver.isConnected.collect { connected ->
                _uiState.update { it.copy(isConnected = connected) }
                if (connected) refresh()
            }
        }
    }

    fun onEvent(event: HomeEvent) {
        when (event) {
            HomeEvent.OnRetry, HomeEvent.OnRefresh -> refresh()
        }
    }

    private fun refresh() {
        if (_uiState.value.isRefreshing) return
        viewModelScope.launch {
            _uiState.update { it.copy(isRefreshing = true) }
            try {
                val profile = runCatching { api.getMyProfile().takeIf { it.isSuccessful }?.body() }.getOrNull()
                val banners = runCatching { api.getBanners().takeIf { it.isSuccessful }?.body() }.getOrNull()
                val lands = runCatching { landRepository.getNearbyLands(limit = 10) }.getOrDefault(emptyList())
                _uiState.update { state -> state.copy(
                    userName = profile?.fullname?.takeIf(String::isNotBlank) ?: state.userName,
                    banners = banners ?: state.banners,
                    nearbyLands = lands.map { land -> HomeLandItem(
                        id = land.id, imageUrl = land.coverImageUrl, price = land.formattedPrice,
                        area = land.formattedArea, district = land.districtOrCity, state = land.stateText
                    ) }
                ) }
            } finally {
                _uiState.update { it.copy(isRefreshing = false) }
            }
        }
    }
}

class HomeViewModelFactory(
    private val api: ApiService,
    private val landRepository: LandRepository,
    private val connectivityObserver: ConnectivityObserver
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(HomeViewModel::class.java)) return HomeViewModel(api, landRepository, connectivityObserver) as T
        throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
    }
}
