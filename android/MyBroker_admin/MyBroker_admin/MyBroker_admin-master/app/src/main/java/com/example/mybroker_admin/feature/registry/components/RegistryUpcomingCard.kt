
package com.example.mybroker_admin.feature.registry.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.mybroker_admin.core.components.RegistryStatusChip
import com.example.mybroker_admin.domain.model.RegistryAssignment

@Composable
fun RegistryUpcomingCard(
    assignment: RegistryAssignment,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier
            .fillMaxWidth()
            .clickable { onClick() }
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = assignment.propertyName,
                        style = MaterialTheme.typography.titleMedium
                    )
                    Text(
                        text = "${assignment.buyerName} & ${assignment.sellerName}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                RegistryStatusChip(status = assignment.status)
            }

            Spacer(modifier = Modifier.height(12.dp))

            RegistryInfoRow(label = "Date", value = assignment.date.ifBlank { "TBD" })
            Spacer(modifier = Modifier.height(6.dp))
            RegistryInfoRow(label = "Time", value = assignment.time.ifBlank { "TBD" })
            Spacer(modifier = Modifier.height(6.dp))
            RegistryInfoRow(label = "Location", value = assignment.location.ifBlank { "TBD" })
        }
    }
}
