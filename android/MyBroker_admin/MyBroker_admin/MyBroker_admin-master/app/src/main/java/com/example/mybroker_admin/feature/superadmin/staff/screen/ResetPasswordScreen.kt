package com.example.mybroker_admin.feature.superadmin.staff.screen



import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavController
import com.example.mybroker_admin.feature.superadmin.staff.viewmodel.StaffViewModel



@Composable
fun ResetPasswordScreen(
    staffId: Int,
    navController: NavController,
    viewModel: StaffViewModel = hiltViewModel()
) {
    var password by remember { mutableStateOf("") }
    var confirmPassword by remember { mutableStateOf("") }
    var localError by remember { mutableStateOf("") }

    val state by viewModel.listState.collectAsState() // ya jo aapka StateFlow naam hai
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(state.successMessage) {
        state.successMessage?.let { msg ->
            snackbarHostState.showSnackbar(msg)   // "Password updated successfully"
            navController.popBackStack()
            viewModel.clearMessages() // success/error null karne ke liye VM method
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
        ) {
            Text("Reset Staff Password", style = MaterialTheme.typography.titleLarge)

            Spacer(Modifier.height(20.dp))

            OutlinedTextField(
                value = password,
                onValueChange = { password = it },
                label = { Text("New Password") },
                singleLine = true
            )

            Spacer(Modifier.height(12.dp))

            OutlinedTextField(
                value = confirmPassword,
                onValueChange = { confirmPassword = it },
                label = { Text("Confirm Password") },
                singleLine = true
            )

            Spacer(Modifier.height(20.dp))

            Button(
                enabled = !state.isActionLoading,
                onClick = {
                    localError = ""
                    if (password.length < 8) { // backend min 8
                        localError = "Password minimum 8 characters"
                        return@Button
                    }
                    if (password != confirmPassword) {
                        localError = "Passwords do not match"
                        return@Button
                    }
                    viewModel.resetStaffPassword(staffId, password)
                    // popBackStack yahan se hata diya
                },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(if (state.isActionLoading) "Updating..." else "Update Password")
            }

            if (localError.isNotEmpty()) {
                Spacer(Modifier.height(10.dp))
                Text(localError, color = Color.Red)
            }

            state.error?.let {
                Spacer(Modifier.height(10.dp))
                Text(it, color = Color.Red)
            }
        }
    }
}
