package com.example.mybroker_admin.feature.superadmin.dashboard.components


import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.mybroker_admin.feature.superadmin.staff.model.Staff

@Composable
fun StaffCard(
    staff: Staff,
    onEdit: () -> Unit,
    onToggleActive: () -> Unit,
    onDelete: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 6.dp),
        elevation = CardDefaults.cardElevation(4.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {

            Text("Name: ${staff.name}")
            Text("Email: ${staff.email}")
            Text("Role: ${staff.role}")
            Text("Active: ${staff.active}")

            Spacer(modifier = Modifier.height(12.dp))

            Row(
                horizontalArrangement = Arrangement.SpaceBetween,
                modifier = Modifier.fillMaxWidth()
            ) {

                TextButton(onClick = onEdit) {
                    Text("Edit")
                }

                TextButton(onClick = onToggleActive) {
                    Text(if (staff.active) "Deactivate" else "Activate")
                }

                TextButton(onClick = onDelete) {
                    Text("Delete")
                }
            }
        }
    }
}
