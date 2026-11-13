package com.example.mybroker_admin.feature.superadmin.staffanalytics.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.mybroker_admin.feature.superadmin.staffanalytics.model.StaffAnalyticsItem

@Composable
fun AdminAnalyticsCard(
    item: StaffAnalyticsItem,
    onClick: (() -> Unit)? = null
) {
    AnalyticsCardShell(onClick = onClick) {
        Text(text = item.name, style = MaterialTheme.typography.titleMedium)
        Text(text = "Mobile: ${item.mobile ?: "-"}")
        Text(text = "Role: Admin")
        Spacer(modifier = Modifier.height(8.dp))

        MetricGrid(
            metrics = listOf(
                "Docs Verified" to item.documentsVerifiedCount,
                "Docs Rejected" to item.documentsRejectedCount,
                "Listings Approved" to item.listingsApproved,
                "Registry Approved" to item.registryApprovedCount,
                "Sold Count" to item.soldCount
            )
        )
    }
}

@Composable
fun FieldOfficerAnalyticsCard(
    item: StaffAnalyticsItem,
    onClick: (() -> Unit)? = null
) {
    AnalyticsCardShell(onClick = onClick) {
        Text(text = item.name, style = MaterialTheme.typography.titleMedium)
        Text(text = "Mobile: ${item.mobile ?: "-"}")
        Text(text = "Role: Field Officer")
        Spacer(modifier = Modifier.height(8.dp))

        MetricGrid(
            metrics = listOf(
                "Site Visits" to item.siteVisitsCount,
                "Registry Visits" to item.registryVisitsCount
            )
        )
    }
}

@Composable
private fun AnalyticsCardShell(
    onClick: (() -> Unit)?,
    content: @Composable () -> Unit
) {
    val modifier = if (onClick == null) {
        Modifier.fillMaxWidth()
    } else {
        Modifier
            .fillMaxWidth()
            .clickable { onClick() }
    }

    Card(
        modifier = modifier,
        elevation = CardDefaults.cardElevation(4.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            content()
        }
    }
}

@Composable
private fun MetricGrid(
    metrics: List<Pair<String, Int>>
) {
    val chunks = metrics.chunked(2)
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        chunks.forEach { row ->
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                row.forEach { (label, value) ->
                    Column(modifier = Modifier.weight(1f)) {
                        Text(text = label, style = MaterialTheme.typography.labelMedium)
                        Text(text = value.toString(), style = MaterialTheme.typography.titleSmall)
                    }
                }

                if (row.size == 1) {
                    Spacer(modifier = Modifier.weight(1f))
                }
            }
        }
    }
}
