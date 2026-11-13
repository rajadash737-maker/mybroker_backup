package com.example.myapplication.ui.feature.auth

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.myapplication.network.ApiClient
import com.example.myapplication.network.AuthRepository
import com.example.myapplication.network.SessionManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class LoginUiState(
    val email: String = "",
    val password: String = "",
    val errorMessage: String? = null,
    val isLoading: Boolean = false
)

class LoginViewModel(context: Context) : ViewModel() {
    private val appContext = context.applicationContext
    private val repository = AuthRepository(ApiClient.also { it.init(appContext) }.apiService, SessionManager(appContext))
    private val _uiState = MutableStateFlow(LoginUiState())
    val uiState: StateFlow<LoginUiState> = _uiState.asStateFlow()

    fun updateEmail(value: String) = _uiState.update { it.copy(email = value, errorMessage = null) }
    fun updatePassword(value: String) = _uiState.update { it.copy(password = value, errorMessage = null) }

    fun login(onSuccess: () -> Unit) {
        val current = _uiState.value
        if (current.email.isBlank() || current.password.isBlank()) {
            _uiState.update { it.copy(errorMessage = "Enter your email or mobile and password") }
            return
        }
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, errorMessage = null) }
            repository.login(current.email.trim(), current.password)
                .onSuccess { _uiState.update { it.copy(isLoading = false) }; onSuccess() }
                .onFailure { error -> _uiState.update { it.copy(isLoading = false, errorMessage = error.message ?: "Login failed") } }
        }
    }
}

class LoginViewModelFactory(private val context: Context) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(LoginViewModel::class.java)) return LoginViewModel(context) as T
        throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
    }
}
