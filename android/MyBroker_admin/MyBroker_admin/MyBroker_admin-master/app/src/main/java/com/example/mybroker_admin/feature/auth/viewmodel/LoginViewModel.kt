package com.example.mybroker_admin.feature.auth.viewmodel

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.core.session.SessionManager
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.repository.AuthRepositoryImpl
import com.example.mybroker_admin.notification.FcmTokenManager
import com.example.mybroker_admin.notification.NotificationSync
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

class LoginViewModel : ViewModel() {

    private val repo = AuthRepositoryImpl(ApiClient.authApi)

    private val _uiState = MutableStateFlow(LoginUiState())
    val uiState: StateFlow<LoginUiState> = _uiState

    fun onEmailChange(value: String) {
        _uiState.update { it.copy(email = value) }
    }

    fun onPasswordChange(value: String) {
        _uiState.update { it.copy(password = value) }
    }

    fun login(context: Context, onSuccess: (String) -> Unit) {
        val email = _uiState.value.email.trim()
        val password = _uiState.value.password

        if (email.isEmpty() || password.isEmpty()) {
            _uiState.update { it.copy(error = "Email and password required") }
            return
        }

        _uiState.update { it.copy(isLoading = true, error = null) }

        viewModelScope.launch {
            try {
                val result = repo.login(email, password)

                if (result.status.equals("Login successful", ignoreCase = true)) {
                    SessionManager.saveLogin(
                        access = result.accessToken,
                        refresh = result.refreshToken,
                        role = result.role,
                        dashboard = result.dashboardKey,
                        fullName = result.fullName,
                        email = result.email
                    )
                    ApiClient.setAccessToken(result.accessToken)
                    FcmTokenManager.refreshToken(context)
                    FcmTokenManager.tryRegisterPendingToken(force = true)
                    NotificationSync.refreshFromServer(context)
                    _uiState.update { it.copy(isLoading = false) }
                    onSuccess(result.dashboardKey ?: "")
                } else {
                    _uiState.update { it.copy(isLoading = false, error = result.status) }
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        error = e.message ?: "Login failed"
                    )
                }
            }
        }
    }
}
