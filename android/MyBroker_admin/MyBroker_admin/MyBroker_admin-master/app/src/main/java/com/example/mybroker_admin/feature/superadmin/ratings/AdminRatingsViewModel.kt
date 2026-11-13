package com.example.mybroker_admin.feature.superadmin.ratings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.remote.dto.AdminRatingListItemDto
import com.example.mybroker_admin.data.repository.AdminRatingRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class AdminRatingsUiState(
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val items: List<AdminRatingListItemDto> = emptyList()
)

class AdminRatingsViewModel : ViewModel() {
    private val repo = AdminRatingRepository(ApiClient.adminListingApi)
    private val _uiState = MutableStateFlow(AdminRatingsUiState())
    val uiState: StateFlow<AdminRatingsUiState> = _uiState

    fun loadRatings() {
        viewModelScope.launch(Dispatchers.IO) {
            _uiState.update { it.copy(isLoading = true, errorMessage = null) }
            runCatching { repo.getRatings() }
                .onSuccess { items ->
                    _uiState.update { it.copy(isLoading = false, items = items) }
                }
                .onFailure { err ->
                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            errorMessage = err.message ?: "Failed to load ratings"
                        )
                    }
                }
        }
    }
}
