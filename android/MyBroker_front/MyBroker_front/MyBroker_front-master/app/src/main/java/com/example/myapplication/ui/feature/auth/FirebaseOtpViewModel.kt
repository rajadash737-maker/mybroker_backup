package com.example.myapplication.ui.feature.auth

import android.app.Activity
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.myapplication.network.ApiClient
import com.example.myapplication.network.FirebaseTokenRequest
import com.example.myapplication.utils.normalizeMobile
import com.google.firebase.FirebaseException
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.PhoneAuthCredential
import com.google.firebase.auth.PhoneAuthOptions
import com.google.firebase.auth.PhoneAuthProvider
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import com.google.android.gms.tasks.Task
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import java.util.concurrent.TimeUnit

data class FirebaseOtpUiState(
    val mobile: String = "",
    val otp: String = "",
    val otpSent: Boolean = false,
    val otpVerified: Boolean = false,
    val loading: Boolean = false,
    val message: String? = null,
    val canResend: Boolean = true,
    val resendSeconds: Int = 0
)

class FirebaseOtpViewModel : ViewModel() {
    private val auth = FirebaseAuth.getInstance()
    private val _uiState = MutableStateFlow(FirebaseOtpUiState())
    val uiState: StateFlow<FirebaseOtpUiState> = _uiState.asStateFlow()
    private var verificationId: String? = null
    private var resendToken: PhoneAuthProvider.ForceResendingToken? = null

    fun updateMobile(value: String) = _uiState.update { it.copy(mobile = value, otpVerified = false) }
    fun updateOtp(value: String) = _uiState.update { it.copy(otp = value.take(8)) }
    fun clearMessage() = _uiState.update { it.copy(message = null) }

    fun sendOtp(activity: Activity, purpose: String) = requestOtp(activity, purpose, null)
    fun resendOtp(activity: Activity, purpose: String) = requestOtp(activity, purpose, resendToken)

    private fun requestOtp(activity: Activity, purpose: String, token: PhoneAuthProvider.ForceResendingToken?) {
        val mobile = normalizeMobile(_uiState.value.mobile)
        if (mobile.length < 10) {
            _uiState.update { it.copy(message = "Enter a valid mobile number") }
            return
        }
        _uiState.update { it.copy(loading = true, message = null) }
        val callback = object : PhoneAuthProvider.OnVerificationStateChangedCallbacks() {
            override fun onVerificationCompleted(credential: PhoneAuthCredential) {
                val code = credential.smsCode
                if (code != null) updateOtp(code)
                verifyCredential(activity, purpose, credential)
            }

            override fun onVerificationFailed(exception: FirebaseException) {
                _uiState.update { it.copy(loading = false, message = exception.localizedMessage ?: "Could not send OTP") }
            }

            override fun onCodeSent(id: String, newToken: PhoneAuthProvider.ForceResendingToken) {
                verificationId = id
                resendToken = newToken
                _uiState.update { it.copy(loading = false, otpSent = true, otpVerified = false, canResend = true, message = "OTP sent") }
            }
        }
        val options = PhoneAuthOptions.newBuilder(auth)
            .setPhoneNumber(if (mobile.startsWith("+")) mobile else "+91$mobile")
            .setTimeout(60L, TimeUnit.SECONDS)
            .setActivity(activity)
            .setCallbacks(callback)
        if (token != null) options.setForceResendingToken(token)
        PhoneAuthProvider.verifyPhoneNumber(options.build())
    }

    fun verifyOtp(purpose: String) {
        val id = verificationId
        val code = _uiState.value.otp
        if (id.isNullOrBlank() || code.isBlank()) {
            _uiState.update { it.copy(message = "Enter the OTP sent to your mobile") }
            return
        }
        _uiState.update { it.copy(loading = true, message = null) }
        verifyCredential(null, purpose, PhoneAuthProvider.getCredential(id, code))
    }

    private fun verifyCredential(activity: Activity?, purpose: String, credential: PhoneAuthCredential) {
        viewModelScope.launch {
            runCatching {
                val firebaseResult = awaitTask(auth.signInWithCredential(credential))
                val idToken = firebaseResult.user?.getIdToken(true)?.let { awaitTask(it).token }
                    ?: error("Could not verify phone number")
                val mobile = normalizeMobile(_uiState.value.mobile)
                ApiClient.apiService.verifyFirebaseToken(
                    FirebaseTokenRequest(id_token = idToken, mobile = mobile, purpose = backendPurpose(purpose))
                )
            }.onSuccess { response ->
                val body = response.body()
                if (response.isSuccessful && body?.status.equals("OTP verified", true)) {
                    _uiState.update { it.copy(loading = false, otpVerified = true, message = "Mobile verified") }
                } else {
                    _uiState.update { it.copy(loading = false, message = body?.status ?: "OTP verification failed") }
                }
            }.onFailure { error ->
                _uiState.update { it.copy(loading = false, message = error.localizedMessage ?: "OTP verification failed") }
            }
        }
    }

    private fun backendPurpose(value: String) = if (value == "forgot_password") "password_reset" else value

    private suspend fun <T> awaitTask(task: Task<T>): T = suspendCancellableCoroutine { continuation ->
        task.addOnSuccessListener { if (continuation.isActive) continuation.resume(it) }
        task.addOnFailureListener { if (continuation.isActive) continuation.resumeWithException(it) }
    }
}
