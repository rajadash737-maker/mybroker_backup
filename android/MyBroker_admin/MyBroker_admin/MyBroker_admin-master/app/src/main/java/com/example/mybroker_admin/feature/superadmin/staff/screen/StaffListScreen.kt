package com.example.mybroker_admin.feature.superadmin.staff.screen

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import com.example.mybroker_admin.core.navigation.Routes
import com.example.mybroker_admin.feature.superadmin.staff.viewmodel.StaffViewModel


@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StaffListScreen(
    navController: NavHostController,
    viewModel: StaffViewModel
) {

    val state by viewModel.listState.collectAsState()
    var selectedRole by remember { mutableStateOf<String?>(null) }
    var searchQuery by remember { mutableStateOf("") }


    LaunchedEffect(Unit) {
        viewModel.loadStaff()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Staff Management") }
            )
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = {
                    navController.navigate(Routes.CREATE_STAFF)
                }
            ) {
                Icon(Icons.Default.Add, contentDescription = "Add Staff")
            }
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

            state.error != null -> {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding),
                    contentAlignment = Alignment.Center
                ) {
                    Text(state.error ?: "Something went wrong")
                }
            }

            state.data.isEmpty() -> {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding),
                    contentAlignment = Alignment.Center
                ) {
                    Text("No staff found")
                }
            }

            else -> {

                val filteredList = state.data.filter {

                    val matchesRole =
                        selectedRole == null || it.role == selectedRole

                    val matchesSearch =
                        it.fullname.contains(searchQuery, ignoreCase = true) ||
                                it.email.contains(searchQuery, ignoreCase = true)

                    matchesRole && matchesSearch
                }


                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding)
                        .padding(16.dp)
                ) {

                    // 🔹 Role Filter Chips (Scrollable)
                    LazyRow(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 12.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {

                        val roles = listOf("ALL", "ADMIN", "FIELD_OFFICER", "ACCOUNTING")

                        items(roles) { role ->

                            FilterChip(
                                selected = selectedRole == role ||
                                        (role == "ALL" && selectedRole == null),
                                onClick = {
                                    selectedRole =
                                        if (role == "ALL") null else role
                                },
                                label = {
                                    Text(
                                        text = role.replace("_", " "),
                                        maxLines = 1
                                    )
                                }
                            )
                        }
                    }

                    // 🔹 Staff List
                    LazyColumn(
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {

                        items(filteredList) { staff ->

                            Card(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable {
                                        navController.navigate(
                                            Routes.staffDetail(staff.id)
                                        )
                                    },
                                elevation = CardDefaults.cardElevation(4.dp)
                            ) {
                                Column(
                                    modifier = Modifier.padding(16.dp)
                                ) {

                                    Text(
                                        text = staff.fullname,
                                        style = MaterialTheme.typography.titleMedium
                                    )

                                    Spacer(modifier = Modifier.height(4.dp))

                                    Text("Email: ${staff.email}")

                                    Text(
                                        "Role: ${
                                            staff.role.replace("_", " ")
                                        }"
                                    )

                                    Spacer(modifier = Modifier.height(6.dp))

                                    Text(
                                        text = if (staff.is_active)
                                            "Status: Active"
                                        else
                                            "Status: Inactive",
                                        color = if (staff.is_active)
                                            MaterialTheme.colorScheme.primary
                                        else
                                            MaterialTheme.colorScheme.error
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
