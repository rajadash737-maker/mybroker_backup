package com.example.myapplication.ui.feature.auth

import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import com.example.myapplication.R
import com.example.myapplication.auth.GoogleSignInCoordinator
import com.example.myapplication.auth.GoogleSignInResult
import com.example.myapplication.notification.FcmTokenManager
import com.example.myapplication.network.ApiClient
import com.example.myapplication.network.AuthRepository
import com.example.myapplication.network.SessionManager
import com.example.myapplication.ui.feature.Screen
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch

@Composable
fun SignupScreenWithOtpUI(navController: NavController) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val googleSignInCoordinator = remember { GoogleSignInCoordinator() }
    val authRepository = remember(context) {
        ApiClient.init(context.applicationContext)
        AuthRepository(
            api = ApiClient.apiService,
            session = SessionManager(context.applicationContext)
        )
    }

    var isAuthenticating by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    Box(modifier = Modifier.fillMaxSize()) {
        Image(
            painter = painterResource(id = R.drawable.background),
            contentDescription = null,
            contentScale = ContentScale.Crop,
            modifier = Modifier.fillMaxSize()
        )
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(Color.Black.copy(alpha = 0.3f))
        )

        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(24.dp)
                .align(Alignment.Center),
            shape = RoundedCornerShape(20.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.15f))
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                Text("Create Account", fontSize = 26.sp, color = Color.White)
                Spacer(modifier = Modifier.height(24.dp))

                Button(
                    onClick = {
                        if (isAuthenticating) return@Button
                        val activity = context.findActivity()
                        if (activity == null) {
                            errorMessage = "Google sign-in is unavailable right now. Please try again."
                            return@Button
                        }

                        scope.launch {
                            isAuthenticating = true
                            errorMessage = null
                            try {
                                when (val signIn = googleSignInCoordinator.getIdToken(activity)) {
                                    is GoogleSignInResult.Success -> {
                                        authRepository.loginWithGoogle(signIn.idToken)
                                            .onSuccess {
                                                FcmTokenManager.tryRegisterPendingToken(
                                                    context = context.applicationContext,
                                                    force = true
                                                )
                                                navController.navigate(Screen.Home.route) {
                                                    popUpTo("login") { inclusive = true }
                                                    launchSingleTop = true
                                                }
                                            }
                                            .onFailure { failure ->
                                                errorMessage = failure.message
                                                    ?: "Sign-in failed. Please try again."
                                            }
                                    }

                                    GoogleSignInResult.Cancelled -> {
                                        errorMessage = "Google sign-in was cancelled. You can try again."
                                    }

                                    GoogleSignInResult.NoGoogleAccount -> {
                                        errorMessage = "No Google account is available. Add an account or try again."
                                    }

                                    is GoogleSignInResult.Failure -> errorMessage = signIn.message
                                }
                            } catch (cancelled: CancellationException) {
                                throw cancelled
                            } catch (_: Exception) {
                                errorMessage = "Sign-in could not be completed. Check your connection and try again."
                            } finally {
                                isAuthenticating = false
                            }
                        }
                    },
                    enabled = !isAuthenticating,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Color.White.copy(alpha = 0.9f),
                        contentColor = Color(0xFF202124)
                    )
                ) {
                    if (isAuthenticating) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(20.dp),
                            strokeWidth = 2.dp,
                            color = Color(0xFF202124)
                        )
                        Spacer(modifier = Modifier.size(10.dp))
                        Text("Signing in…")
                    } else {
                        Text("Continue with Google", fontSize = 16.sp)
                    }
                }

                if (errorMessage != null) {
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = errorMessage.orEmpty(),
                        color = Color.White,
                        style = MaterialTheme.typography.bodyMedium,
                        textAlign = TextAlign.Center
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))
                TextButton(
                    onClick = { navController.navigate("login") },
                    enabled = !isAuthenticating
                ) {
                    Text("Already have an account? Login", color = Color.White)
                }
            }
        }
    }
}

private tailrec fun Context.findActivity(): Activity? = when (this) {
    is Activity -> this
    is ContextWrapper -> baseContext.findActivity()
    else -> null
}
