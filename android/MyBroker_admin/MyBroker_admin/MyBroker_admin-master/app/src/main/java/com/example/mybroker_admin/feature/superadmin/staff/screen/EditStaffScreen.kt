package com.example.mybroker_admin.feature.superadmin.staff.screen

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import com.example.mybroker_admin.core.model.UserRole
import com.example.mybroker_admin.feature.superadmin.staff.viewmodel.StaffViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EditStaffScreen(
    staffId: Int,
    navController: NavHostController,
    viewModel: StaffViewModel
) {
    val state by viewModel.listState.collectAsState()
    val staff = state.data.find { it.id == staffId }

    var name by remember { mutableStateOf("") }
    var email by remember { mutableStateOf("") }
    var selectedRole by remember { mutableStateOf(UserRole.ADMIN) }

    LaunchedEffect(staffId) {
        if (state.data.isEmpty() && !state.isLoading) viewModel.loadStaff()
    }

    LaunchedEffect(staff?.id) {
        staff?.let {
            name = it.fullname
            email = it.email
            selectedRole = runCatching { UserRole.valueOf(it.role) }.getOrDefault(UserRole.ADMIN)
        }
    }

    LaunchedEffect(state.successMessage) {
        if (state.successMessage == "Staff updated successfully") {
            navController.popBackStack()
        }
    }

    Scaffold(
        topBar = { TopAppBar(title = { Text("Edit Staff") }) }
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .padding(16.dp)
        ) {
            OutlinedTextField(
                value = name,
                onValueChange = { name = it },
                label = { Text("Name") },
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(8.dp))

            OutlinedTextField(
                value = email,
                onValueChange = { email = it },
                label = { Text("Email") },
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(8.dp))

            state.error?.let {
                Text(
                    text = it,
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(8.dp))
            }

            Button(
                onClick = {
                    viewModel.updateStaff(
                        staffId = staffId,
                        name = name,
                        email = email,
                        role = selectedRole
                    )
                },
                enabled = !state.isActionLoading,
                modifier = Modifier.fillMaxWidth()
            ) {
                if (state.isActionLoading) {
                    CircularProgressIndicator(
                        strokeWidth = 2.dp,
                        modifier = Modifier.size(18.dp),
                        color = Color.White
                    )
                } else {
                    Text("Update Staff")
                }
            }
        }
    }
}
