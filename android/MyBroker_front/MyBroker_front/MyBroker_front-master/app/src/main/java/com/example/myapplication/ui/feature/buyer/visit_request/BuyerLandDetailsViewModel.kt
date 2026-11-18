package com.example.myapplication.ui.feature.buyer.visit_request

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.myapplication.ui.feature.buyer.domain.repository.LandRepository
import com.example.myapplication.ui.feature.buyer.land_detail.LandDetail
import com.example.myapplication.ui.feature.buyer.domain.model.BuyerOffer
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class BuyerLandDetailsUiState(
    val land: LandDetail? = null,
    val offer: BuyerOffer? = null,
    val loading: Boolean = false,
    val error: String? = null
)

class BuyerLandDetailsViewModel(private val repository: LandRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(BuyerLandDetailsUiState())
    val uiState: StateFlow<BuyerLandDetailsUiState> = _uiState.asStateFlow()

    fun load(requestId: Int) {
        viewModelScope.launch {
            _uiState.value = BuyerLandDetailsUiState(loading = true)
            runCatching { repository.getBuyerLandDetail(requestId) }
                .onSuccess { land ->
                    val buyerOffer = runCatching {
                        val offers = repository.getBuyerOffers().filter { it.requestId == requestId }
                        offers.firstOrNull { it.bookingId != null }
                            ?: offers.filter { it.offerStatus.equals("accepted", ignoreCase = true) }
                                .maxByOrNull { it.updatedAt }
                            ?: offers.maxByOrNull { it.updatedAt }
                    }
                        .getOrNull()
                    _uiState.value = BuyerLandDetailsUiState(land = land, offer = buyerOffer)
                }
                .onFailure { _uiState.value = BuyerLandDetailsUiState(error = it.message ?: "Unable to load land details") }
        }
    }
}

class BuyerLandDetailsViewModelFactory(private val repository: LandRepository) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(BuyerLandDetailsViewModel::class.java)) return BuyerLandDetailsViewModel(repository) as T
        throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
    }
}
