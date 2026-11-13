package com.example.mybroker_admin.feature.superadmin.staffanalytics.screen

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Block
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Group
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedIconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import com.example.mybroker_admin.feature.superadmin.dashboard.components.StatCard
import com.example.mybroker_admin.feature.superadmin.staffanalytics.components.AdminAnalyticsCard
import com.example.mybroker_admin.feature.superadmin.staffanalytics.components.FieldOfficerAnalyticsCard
import com.example.mybroker_admin.feature.superadmin.staffanalytics.model.StaffAnalyticsDateFilter
import com.example.mybroker_admin.feature.superadmin.staffanalytics.model.StaffAnalyticsRoleTab
import com.example.mybroker_admin.feature.superadmin.staffanalytics.viewmodel.StaffAnalyticsViewModel
import java.time.LocalDate
import java.time.format.DateTimeFormatter

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StaffAnalyticsScreen(navController: NavHostController) {
    val vm: StaffAnalyticsViewModel = viewModel()
    val state by vm.state.collectAsState()
    val context = LocalContext.current

    val dateFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd")

    val roleTabs = listOf(
        StaffAnalyticsRoleTab.ALL,
        StaffAnalyticsRoleTab.ADMIN,
        StaffAnalyticsRoleTab.FIELD_OFFICER
    )

    val filteredStaff = when (state.selectedRoleTab) {
        StaffAnalyticsRoleTab.ALL -> state.staff
        StaffAnalyticsRoleTab.ADMIN -> state.staff.filter { it.role.equals("ADMIN", true) }
        StaffAnalyticsRoleTab.FIELD_OFFICER -> state.staff.filter { it.role.equals("FIELD_OFFICER", true) }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Staff Analytics") },
                navigationIcon = {
                    androidx.compose.material3.TextButton(onClick = { navController.popBackStack() }) {
                        Text("Back")
                    }
                }
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .padding(padding)
                .padding(16.dp)
        ) {
            item {
                Text("Summary", style = MaterialTheme.typography.titleLarge)
                Spacer(modifier = Modifier.height(12.dp))
            }

            item {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    StatCard(
                        title = "Total Staff",
                        value = state.summary.totalStaffCount.toString(),
                        icon = Icons.Default.Group,
                        modifier = Modifier.weight(1f)
                    )
                    StatCard(
                        title = "Site Visits",
                        value = state.summary.totalSiteVisits.toString(),
                        icon = Icons.Default.LocationOn,
                        modifier = Modifier.weight(1f)
                    )
                }
            }

            item { Spacer(modifier = Modifier.height(12.dp)) }

            item {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    StatCard(
                        title = "Verified Docs",
                        value = state.summary.totalVerifiedDocuments.toString(),
                        icon = Icons.Default.CheckCircle,
                        modifier = Modifier.weight(1f)
                    )
                    StatCard(
                        title = "Rejected Docs",
                        value = state.summary.totalRejectedDocuments.toString(),
                        icon = Icons.Default.Block,
                        modifier = Modifier.weight(1f)
                    )
                }
            }

            item { Spacer(modifier = Modifier.height(20.dp)) }

            item {
                TabRow(selectedTabIndex = roleTabs.indexOf(state.selectedRoleTab)) {
                    roleTabs.forEach { tab ->
                        val label = when (tab) {
                            StaffAnalyticsRoleTab.ALL -> "All"
                            StaffAnalyticsRoleTab.ADMIN -> "Admin"
                            StaffAnalyticsRoleTab.FIELD_OFFICER -> "Field Officer"
                        }
                        Tab(
                            selected = state.selectedRoleTab == tab,
                            onClick = { vm.onRoleTabSelected(tab) },
                            text = { Text(label) }
                        )
                    }
                }
            }

            item { Spacer(modifier = Modifier.height(16.dp)) }

            item {
                Text("Date Filters", style = MaterialTheme.typography.titleMedium)
                Spacer(modifier = Modifier.height(8.dp))
            }

            item {
                Row(
                    modifier = Modifier.horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    FilterChip(
                        selected = state.dateFilter == StaffAnalyticsDateFilter.ALL,
                        onClick = { vm.onDateFilterSelected(StaffAnalyticsDateFilter.ALL) },
                        label = { Text("All") }
                    )
                    FilterChip(
                        selected = state.dateFilter == StaffAnalyticsDateFilter.TODAY,
                        onClick = { vm.onDateFilterSelected(StaffAnalyticsDateFilter.TODAY) },
                        label = { Text("Today") }
                    )
                    FilterChip(
                        selected = state.dateFilter == StaffAnalyticsDateFilter.WEEK,
                        onClick = { vm.onDateFilterSelected(StaffAnalyticsDateFilter.WEEK) },
                        label = { Text("Week") }
                    )
                    FilterChip(
                        selected = state.dateFilter == StaffAnalyticsDateFilter.MONTH,
                        onClick = { vm.onDateFilterSelected(StaffAnalyticsDateFilter.MONTH) },
                        label = { Text("Month") }
                    )
                    FilterChip(
                        selected = state.dateFilter == StaffAnalyticsDateFilter.CUSTOM,
                        onClick = { vm.onDateFilterSelected(StaffAnalyticsDateFilter.CUSTOM) },
                        label = { Text("Custom") }
                    )
                }
            }

            if (state.dateFilter == StaffAnalyticsDateFilter.CUSTOM) {
                item { Spacer(modifier = Modifier.height(8.dp)) }
                item {
                    OutlinedTextField(
                        value = state.customStart,
                        onValueChange = vm::onCustomStartChange,
                        label = { Text("Start (YYYY-MM-DD)") },
                        modifier = Modifier.fillMaxWidth(),
                        readOnly = true,
                        trailingIcon = {
                            OutlinedIconButton(
                                onClick = {
                                    val now = LocalDate.now()
                                    val dialog = android.app.DatePickerDialog(
                                        context,
                                        { _, y, m, d ->
                                            val date = LocalDate.of(y, m + 1, d)
                                            vm.onCustomStartChange(date.format(dateFormatter))
                                        },
                                        now.year,
                                        now.monthValue - 1,
                                        now.dayOfMonth
                                    )
                                    dialog.show()
                                }
                            ) {
                                Text("Pick")
                            }
                        }
                    )
                }
                item { Spacer(modifier = Modifier.height(8.dp)) }
                item {
                    OutlinedTextField(
                        value = state.customEnd,
                        onValueChange = vm::onCustomEndChange,
                        label = { Text("End (YYYY-MM-DD)") },
                        modifier = Modifier.fillMaxWidth(),
                        readOnly = true,
                        trailingIcon = {
                            OutlinedIconButton(
                                onClick = {
                                    val now = LocalDate.now()
                                    val dialog = android.app.DatePickerDialog(
                                        context,
                                        { _, y, m, d ->
                                            val date = LocalDate.of(y, m + 1, d)
                                            vm.onCustomEndChange(date.format(dateFormatter))
                                        },
                                        now.year,
                                        now.monthValue - 1,
                                        now.dayOfMonth
                                    )
                                    dialog.show()
                                }
                            ) {
                                Text("Pick")
                            }
                        }
                    )
                }
                item { Spacer(modifier = Modifier.height(8.dp)) }
                item {
                    androidx.compose.material3.Button(
                        onClick = vm::applyCustomRange,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Apply Range")
                    }
                }
                if (!state.filterMessage.isNullOrBlank()) {
                    item { Spacer(modifier = Modifier.height(6.dp)) }
                    item {
                        Text(
                            text = state.filterMessage ?: "",
                            color = MaterialTheme.colorScheme.error
                        )
                    }
                }
            }

            item { Spacer(modifier = Modifier.height(20.dp)) }

            item {
                Text("Staff Performance", style = MaterialTheme.typography.titleMedium)
                Spacer(modifier = Modifier.height(8.dp))
            }

            if (state.isLoading) {
                item {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
                        CircularProgressIndicator()
                    }
                }
            } else if (!state.error.isNullOrBlank()) {
                item {
                    Text(state.error ?: "Failed to load analytics", color = MaterialTheme.colorScheme.error)
                }
            } else if (filteredStaff.isEmpty()) {
                item { Text("No staff data available for this filter.") }
            } else {
                items(filteredStaff.size) { idx ->
                    val staff = filteredStaff[idx]
                    val isAdmin = staff.role.equals("ADMIN", true)
                    if (isAdmin) {
                        AdminAnalyticsCard(item = staff)
                    } else {
                        FieldOfficerAnalyticsCard(item = staff)
                    }
                    Spacer(modifier = Modifier.height(10.dp))
                }
            }
        }
    }
}
