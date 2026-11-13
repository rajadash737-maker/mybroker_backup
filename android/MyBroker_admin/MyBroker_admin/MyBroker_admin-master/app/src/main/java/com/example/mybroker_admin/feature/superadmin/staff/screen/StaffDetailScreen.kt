package com.example.mybroker_admin.feature.superadmin.staff.screen

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController


import com.example.mybroker_admin.core.navigation.Routes
import com.example.mybroker_admin.feature.superadmin.staff.viewmodel.StaffViewModel
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.material3.ExperimentalMaterial3Api

import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment

import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue



@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StaffDetailScreen(
    staffId: Int,
    navController: NavHostController,
    viewModel: StaffViewModel
) {

    val state by viewModel.listState.collectAsState()
    val staff = state.data.find { it.id == staffId }

    var showDeleteDialog by remember { mutableStateOf(false) }

    LaunchedEffect(staffId) {
        if (state.data.isEmpty() && !state.isLoading) {
            viewModel.loadStaff()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Staff Detail") })
        }
    ) { padding ->

        when {
            state.isLoading -> {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator()
                }
            }

            staff == null -> {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding),
                    contentAlignment = Alignment.Center
                ) {
                    Text("Staff not found")
                }
            }

            else -> {

                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding)
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(20.dp)
                ) {

                    // 🔹 STAFF INFO CARD
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        elevation = CardDefaults.cardElevation(6.dp)
                    ) {
                        Column(
                            modifier = Modifier.padding(20.dp),
                            verticalArrangement = Arrangement.spacedBy(8.dp)
                        ) {

                            Text(
                                text = staff.fullname,
                                style = MaterialTheme.typography.titleLarge
                            )

                            Text("Email: ${staff.email}")

                            Text(
                                "Role: ${
                                    staff.role.replace("_", " ")
                                }"
                            )

                            staff.mobile?.let {
                                Text("Mobile: $it")
                            }

                            staff.username?.let {
                                Text("Username: $it")
                            }

                            staff.created_at?.let {
                                Text("Created At: $it")
                            }

                            val statusColor =
                                if (staff.is_active)
                                    MaterialTheme.colorScheme.primary
                                else
                                    MaterialTheme.colorScheme.error

                            AssistChip(
                                onClick = {},
                                label = {
                                    Text(
                                        if (staff.is_active) "Active"
                                        else "Inactive"
                                    )
                                },
                                colors = AssistChipDefaults.assistChipColors(
                                    containerColor = statusColor.copy(alpha = 0.15f),
                                    labelColor = statusColor
                                )
                            )
                        }
                    }

                    // 🔹 ACTION BUTTONS
                    Column(
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {

                        Button(
                            onClick = {
                                navController.navigate(
                                    Routes.editStaff(staff.id)
                                )
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("✏ Edit Staff")
                        }

                        OutlinedButton(
                            onClick = {
                                viewModel.toggleActive(
                                    staffId = staff.id,
                                    currentIsActive = staff.is_active
                                )
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(
                                if (staff.is_active)
                                    "Deactivate"
                                else
                                    "Activate"
                            )
                        }

                        OutlinedButton(
                            onClick = {
                                navController.navigate("reset_password/${staff.id}")
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Reset Password")
                        }

                        Button(
                            onClick = { showDeleteDialog = true },
                            colors = ButtonDefaults.buttonColors(
                                containerColor = MaterialTheme.colorScheme.error
                            ),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Delete Staff")
                        }
                    }
                }

                // 🔹 DELETE DIALOG
                if (showDeleteDialog) {
                    AlertDialog(
                        onDismissRequest = { showDeleteDialog = false },
                        title = { Text("Delete Staff") },
                        text = {
                            Text("Are you sure you want to delete ${staff.fullname}?")
                        },
                        confirmButton = {
                            TextButton(
                                onClick = {
                                    viewModel.deleteStaff(staff.id)
                                    showDeleteDialog = false
                                    navController.popBackStack()
                                }
                            ) {
                                Text("Delete", color = MaterialTheme.colorScheme.error)
                            }
                        },
                        dismissButton = {
                            TextButton(
                                onClick = { showDeleteDialog = false }
                            ) {
                                Text("Cancel")
                            }
                        }
                    )
                }
            }
        }
    }
}
