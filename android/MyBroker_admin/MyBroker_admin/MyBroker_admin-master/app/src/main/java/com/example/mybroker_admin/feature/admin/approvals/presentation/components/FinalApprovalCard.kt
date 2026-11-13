package com.example.mybroker_admin.feature.admin.approvals.presentation.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.mybroker_admin.feature.admin.approvals.model.FinalApprovalListing

@Composable
fun FinalApprovalCard(
    listing: FinalApprovalListing,
    onApproveGoLive: () -> Unit,
    onReject: (String) -> Unit,
    onReassign: () -> Unit
) {
    var showRejectDialog by remember { mutableStateOf(false) }
    var rejectReason by remember { mutableStateOf("") }
    var showReassignDialog by remember { mutableStateOf(false) }

    if (showRejectDialog) {
        AlertDialog(
            onDismissRequest = { showRejectDialog = false },
            title = { Text("Reject Listing") },
            text = {
                OutlinedTextField(
                    value = rejectReason,
                    onValueChange = { rejectReason = it },
                    label = { Text("Rejection Reason") },
                    singleLine = false,
                    minLines = 3
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        val reason = rejectReason.trim()
                        if (reason.isNotEmpty()) {
                            onReject(reason)
                            rejectReason = ""
                            showRejectDialog = false
                        }
                    }
                ) { Text("Reject") }
            },
            dismissButton = {
                OutlinedButton(
                    onClick = {
                        rejectReason = ""
                        showRejectDialog = false
                    }
                ) { Text("Cancel") }
            }
        )
    }

    if (showReassignDialog) {
        AlertDialog(
            onDismissRequest = { showReassignDialog = false },
            title = { Text("Reassign Case") },
            text = { Text("Are you sure? This case will be moved back to field officer queue.") },
            confirmButton = {
                Button(
                    onClick = {
                        showReassignDialog = false
                        onReassign()
                    }
                ) { Text("Yes, Reassign") }
            },
            dismissButton = {
                OutlinedButton(onClick = { showReassignDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        elevation = CardDefaults.cardElevation(6.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("Listing ID: LST-${listing.id}")
            Spacer(modifier = Modifier.height(4.dp))
            Text("Seller: ${listing.sellerName}")
            Text("Mobile: ${listing.sellerMobile}")
            Text("Location: ${listing.location}")

            Spacer(modifier = Modifier.height(6.dp))
            Text("Field Officer: ${listing.officerName}")
            Text("Officer Mobile: ${listing.officerMobile}")
            Text("Visit Date: ${listing.visitDate}")

            Spacer(modifier = Modifier.height(8.dp))
            FieldPhotoSection(listing.fieldPhotos)

            Spacer(modifier = Modifier.height(12.dp))
            RecommendationBadge(listing.recommendation)

            Spacer(modifier = Modifier.height(6.dp))
            Text("Report: ${listing.reportSummary}")

            Spacer(modifier = Modifier.height(16.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = onApproveGoLive,
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Approve & Go Live")
                }

                OutlinedButton(
                    onClick = { showRejectDialog = true },
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Reject")
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            OutlinedButton(
                onClick = { showReassignDialog = true },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Reassign To Field Officer")
            }
        }
    }
}
