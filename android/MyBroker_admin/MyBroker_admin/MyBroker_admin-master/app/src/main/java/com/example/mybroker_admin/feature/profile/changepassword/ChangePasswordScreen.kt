package com.example.mybroker_admin.feature.profile.changepassword

import android.widget.Toast
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.delay

@Composable
fun ChangePasswordScreen(
    viewModel: ChangePasswordViewModel = viewModel(),
    onBack: () -> Unit,
    onLogout: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val context = LocalContext.current

    LaunchedEffect(uiState.logoutRequired) {
        if (uiState.logoutRequired) {
            Toast.makeText(
                context,
                uiState.successMessage ?: "Password changed successfully",
                Toast.LENGTH_SHORT
            ).show()
            delay(1400)
            viewModel.onLogoutHandled()
            onLogout()
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF6F8FC))
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(
                onClick = {
                    if (uiState.step == ChangePasswordStep.SET_NEW_PASSWORD) {
                        viewModel.goBackOneStep()
                    } else {
                        onBack()
                    }
                }
            ) {
                Icon(Icons.Default.ArrowBack, contentDescription = "Back")
            }
            Text(
                text = "Change Password",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.SemiBold
            )
        }

        Surface(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(24.dp),
            color = Color.White,
            tonalElevation = 2.dp
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                StepHeader(uiState = uiState)

                uiState.globalMessage?.let { message ->
                    Surface(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(16.dp),
                        color = Color(0xFFFFF3F0)
                    ) {
                        Text(
                            text = message,
                            color = Color(0xFFB3261E),
                            modifier = Modifier.padding(14.dp),
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }
                }

                AnimatedContent(
                    targetState = uiState.step,
                    transitionSpec = {
                        (slideInHorizontally { fullWidth -> fullWidth / 4 } + fadeIn()) togetherWith
                            (slideOutHorizontally { fullWidth -> -fullWidth / 4 } + fadeOut())
                    },
                    label = "change_password_step"
                ) { step ->
                    when (step) {
                        ChangePasswordStep.VERIFY_IDENTITY -> Step1Form(
                            state = uiState,
                            onNameChange = viewModel::onNameChange,
                            onEmailChange = viewModel::onEmailChange,
                            onCurrentPasswordChange = viewModel::onCurrentPasswordChange,
                            onCurrentPasswordToggle = viewModel::toggleCurrentPasswordVisibility,
                            onContinue = viewModel::continueToStepTwo
                        )

                        ChangePasswordStep.SET_NEW_PASSWORD -> Step2Form(
                            state = uiState,
                            onNewPasswordChange = viewModel::onNewPasswordChange,
                            onConfirmPasswordChange = viewModel::onConfirmPasswordChange,
                            onNewPasswordToggle = viewModel::toggleNewPasswordVisibility,
                            onConfirmPasswordToggle = viewModel::toggleConfirmPasswordVisibility,
                            onBack = viewModel::goBackOneStep,
                            onSubmit = viewModel::submitChangePassword
                        )

                        ChangePasswordStep.SUCCESS -> SuccessStep(
                            message = uiState.successMessage ?: "Password changed successfully"
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun Step1Form(
    state: ChangePasswordUiState,
    onNameChange: (String) -> Unit,
    onEmailChange: (String) -> Unit,
    onCurrentPasswordChange: (String) -> Unit,
    onCurrentPasswordToggle: () -> Unit,
    onContinue: () -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(
            text = "Step 1 of 2",
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.primary
        )
        Text(
            text = "Verify your identity before creating a new password.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        OutlinedTextField(
            value = state.name,
            onValueChange = onNameChange,
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Name") },
            readOnly = state.isNameReadOnly,
            isError = state.errors.name != null,
            supportingText = {
                state.errors.name?.let { Text(it) }
            }
        )

        OutlinedTextField(
            value = state.roleLabel,
            onValueChange = {},
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Role") },
            readOnly = true
        )

        OutlinedTextField(
            value = state.email,
            onValueChange = onEmailChange,
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Email") },
            keyboardOptions = KeyboardOptions(
                keyboardType = KeyboardType.Email,
                imeAction = ImeAction.Next
            ),
            isError = state.errors.email != null,
            supportingText = {
                state.errors.email?.let { Text(it) }
            }
        )

        PasswordField(
            value = state.currentPassword,
            onValueChange = onCurrentPasswordChange,
            label = "Current Password",
            visible = state.isCurrentPasswordVisible,
            onVisibilityToggle = onCurrentPasswordToggle,
            error = state.errors.currentPassword
        )

        Button(
            onClick = onContinue,
            modifier = Modifier.fillMaxWidth(),
            enabled = state.canContinue && !state.isBootstrapping
        ) {
            if (state.isBootstrapping) {
                CircularProgressIndicator(strokeWidth = 2.dp)
            } else {
                Text("Continue")
            }
        }
    }
}

@Composable
fun Step2Form(
    state: ChangePasswordUiState,
    onNewPasswordChange: (String) -> Unit,
    onConfirmPasswordChange: (String) -> Unit,
    onNewPasswordToggle: () -> Unit,
    onConfirmPasswordToggle: () -> Unit,
    onBack: () -> Unit,
    onSubmit: () -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(
            text = "Step 2 of 2",
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.primary
        )
        Text(
            text = "Create a strong password with uppercase, lowercase, and numbers.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        PasswordField(
            value = state.newPassword,
            onValueChange = onNewPasswordChange,
            label = "New Password",
            visible = state.isNewPasswordVisible,
            onVisibilityToggle = onNewPasswordToggle,
            error = state.errors.newPassword
        )

        PasswordField(
            value = state.confirmPassword,
            onValueChange = onConfirmPasswordChange,
            label = "Confirm New Password",
            visible = state.isConfirmPasswordVisible,
            onVisibilityToggle = onConfirmPasswordToggle,
            error = state.errors.confirmPassword
        )

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            OutlinedButton(
                onClick = onBack,
                modifier = Modifier.weight(1f),
                enabled = !state.isSubmitting
            ) {
                Text("Back")
            }

            Button(
                onClick = onSubmit,
                modifier = Modifier.weight(1f),
                enabled = state.canSubmit && !state.isSubmitting
            ) {
                if (state.isSubmitting) {
                    CircularProgressIndicator(strokeWidth = 2.dp)
                } else {
                    Text("Save & Change Password")
                }
            }
        }
    }
}

@Composable
private fun SuccessStep(message: String) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Spacer(modifier = Modifier.height(8.dp))
        Icon(
            imageVector = Icons.Default.CheckCircle,
            contentDescription = null,
            tint = Color(0xFF1B8F4B),
            modifier = Modifier.height(64.dp)
        )
        Text(
            text = "Password Changed Successfully",
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.SemiBold
        )
        Text(
            text = "$message\nYou'll be signed out for security.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
private fun StepHeader(uiState: ChangePasswordUiState) {
    val progress = when (uiState.step) {
        ChangePasswordStep.VERIFY_IDENTITY -> 0.5f
        ChangePasswordStep.SET_NEW_PASSWORD -> 1f
        ChangePasswordStep.SUCCESS -> 1f
    }

    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text(
            text = "Secure Password Update",
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.SemiBold
        )
        Text(
            text = "This flow works for Admin, Field Officer, and Accountant accounts through one shared service.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        LinearProgressIndicator(
            progress = progress,
            modifier = Modifier.fillMaxWidth()
        )
    }
}

@Composable
private fun PasswordField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    visible: Boolean,
    onVisibilityToggle: () -> Unit,
    error: String?
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        modifier = Modifier.fillMaxWidth(),
        label = { Text(label) },
        visualTransformation = if (visible) VisualTransformation.None else PasswordVisualTransformation(),
        keyboardOptions = KeyboardOptions(
            keyboardType = KeyboardType.Password,
            imeAction = ImeAction.Done
        ),
        trailingIcon = {
            IconButton(onClick = onVisibilityToggle) {
                Icon(
                    imageVector = if (visible) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                    contentDescription = if (visible) "Hide password" else "Show password"
                )
            }
        },
        isError = error != null,
        supportingText = {
            error?.let { Text(it) }
        }
    )
}
