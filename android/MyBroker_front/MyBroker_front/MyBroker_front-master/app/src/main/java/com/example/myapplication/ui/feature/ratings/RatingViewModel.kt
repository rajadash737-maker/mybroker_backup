package com.example.myapplication.ui.feature.ratings

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.myapplication.network.ApiClient
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class RatingUiState(
    val summaryAverage: Double = 0.0,
    val summaryCount: Int = 0,
    val ratings: List<RatingListItemResponse> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null
)

class RatingViewModel(context: Context) : ViewModel() {
    private val appContext = context.applicationContext
    private val _uiState = MutableStateFlow(RatingUiState())
    val uiState: StateFlow<RatingUiState> = _uiState.asStateFlow()

    fun loadSummaryForCurrentUser() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            runCatching {
                ApiClient.init(appContext)
                val summary = ApiClient.apiService.getMyRatingSummary().takeIf { it.isSuccessful }?.body()
                val ratings = ApiClient.apiService.getMyRatingsList().takeIf { it.isSuccessful }?.body().orEmpty()
                summary to ratings
            }.onSuccess { (summary, ratings) ->
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    summaryAverage = summary?.average ?: 0.0,
                    summaryCount = summary?.totalReviews ?: 0,
                    ratings = ratings
                )
            }.onFailure { _uiState.value = _uiState.value.copy(isLoading = false, error = it.message) }
        }
    }
}

class RatingViewModelFactory(private val context: Context) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(RatingViewModel::class.java)) return RatingViewModel(context) as T
        throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
    }
}
