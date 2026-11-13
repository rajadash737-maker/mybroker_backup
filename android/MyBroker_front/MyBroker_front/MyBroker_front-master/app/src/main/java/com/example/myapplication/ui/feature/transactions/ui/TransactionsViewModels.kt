package com.example.myapplication.ui.feature.transactions.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.myapplication.ui.feature.transactions.data.remote.TransactionDto
import com.example.myapplication.ui.feature.transactions.data.repository.TransactionRepositoryImpl
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class TransactionsUiState(val items: List<TransactionDto> = emptyList(), val loading: Boolean = false, val error: String? = null)
data class TransactionDetailUiState(val item: TransactionDto? = null, val loading: Boolean = false, val error: String? = null)

class TransactionsViewModel(private val repository: TransactionRepositoryImpl) : ViewModel() {
    private val _uiState = MutableStateFlow(TransactionsUiState())
    val uiState: StateFlow<TransactionsUiState> = _uiState.asStateFlow()
    init { refresh() }
    fun refresh() { viewModelScope.launch {
        _uiState.value = _uiState.value.copy(loading = true, error = null)
        runCatching { repository.list() }.onSuccess { _uiState.value = TransactionsUiState(items = it) }
            .onFailure { _uiState.value = TransactionsUiState(error = it.message ?: "Unable to load transactions") }
    } }
}

class TransactionDetailViewModel(private val repository: TransactionRepositoryImpl, private val transactionId: String) : ViewModel() {
    private val _uiState = MutableStateFlow(TransactionDetailUiState(loading = true))
    val uiState: StateFlow<TransactionDetailUiState> = _uiState.asStateFlow()
    init { viewModelScope.launch {
        runCatching { repository.detail(transactionId) }.onSuccess { _uiState.value = TransactionDetailUiState(item = it) }
            .onFailure { _uiState.value = TransactionDetailUiState(error = it.message ?: "Unable to load transaction") }
    } }
}

class TransactionsViewModelFactory(private val repository: TransactionRepositoryImpl) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST") override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(TransactionsViewModel::class.java)) return TransactionsViewModel(repository) as T
        throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
    }
}

class TransactionDetailViewModelFactory(private val repository: TransactionRepositoryImpl, private val transactionId: String) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST") override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(TransactionDetailViewModel::class.java)) return TransactionDetailViewModel(repository, transactionId) as T
        throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
    }
}
