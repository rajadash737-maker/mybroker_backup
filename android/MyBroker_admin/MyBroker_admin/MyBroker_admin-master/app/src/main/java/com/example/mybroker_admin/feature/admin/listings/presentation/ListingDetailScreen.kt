package com.example.mybroker_admin.feature.admin.listings.presentation

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.mybroker_admin.feature.admin.listings.model.AdminListingDetail
import com.example.mybroker_admin.feature.admin.listings.presentation.components.SectionCard
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.clickable
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.platform.LocalContext
import com.example.mybroker_admin.data.remote.PrivatePdfViewer
import coil.compose.AsyncImage
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.Alignment
import androidx.compose.ui.graphics.Color


@Composable
fun AdminListingDetailScreen(
    detail: AdminListingDetail?,
    isLoading: Boolean,
    errorMessage: String?,
    rejectReason: String,
    onRejectReasonChange: (String) -> Unit,
    onReject: () -> Unit,
    onForwardToField: () -> Unit
) {
    val context = LocalContext.current
    val documentScope = rememberCoroutineScope()

    if (isLoading) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp)
        ) {
            CircularProgressIndicator()
        }
        return
    }

    if (!errorMessage.isNullOrBlank()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp)
        ) {
            Text(text = errorMessage, color = MaterialTheme.colorScheme.error)
        }
        return
    }

    if (detail == null) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp)
        ) {
            Text("Listing not found")
        }
        return
    }

    val isRejected = detail.status.equals("REJECTED", ignoreCase = true)
    val isLive = detail.status.equals("LIVE", ignoreCase = true)

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
            .verticalScroll(rememberScrollState())
    ) {
        Text("Listing Review", style = MaterialTheme.typography.headlineSmall)
        Spacer(Modifier.height(16.dp))

        SectionCard(title = "Seller Details") {
            Text("Name: ${detail.sellerName}")
            Text("Mobile: ${detail.sellerMobile}")
            Text("Seller Type: ${detail.ownershipType}")
            Text("Category: ${detail.sellerCategory}")
        }

        Spacer(Modifier.height(12.dp))

        SectionCard(title = "Land Photos") {
            if (detail.photos.isEmpty()) {
                Text("No photos uploaded")
            } else {
                LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    items(detail.photos) { url ->
                        AsyncImage(
                            model = url,
                            contentDescription = "Land photo",
                            modifier = Modifier
                                .width(140.dp)
                                .height(90.dp)
                                .background(Color(0xFFEFEFEF), RoundedCornerShape(10.dp)),
                            alignment = Alignment.Center
                        )
                    }
                }
            }
        }

        Spacer(Modifier.height(12.dp))

        SectionCard(title = "Land Details") {
            Text("Title: ${detail.title}")
            Text("Type: ${detail.landType}")
            Text("Area: ${detail.area}")
            Text("City: ${detail.city}")
            Text("State: ${detail.state}")
            Text("Pincode: ${detail.pincode}")
        }

        Spacer(Modifier.height(12.dp))

        SectionCard(title = "Pricing") {
            Text("Price Type: ${detail.priceType}")
            Text("Expected Price: ${detail.expectedPrice}")
            Text("Negotiable: ${if (detail.negotiable) "Yes" else "No"}")
        }

        Spacer(Modifier.height(12.dp))

        SectionCard(title = "Documents Uploaded") {
            if (detail.documents.isEmpty()) {
                Text("No documents uploaded")
            } else {
                detail.documents.forEach { doc ->
                    Text(
                        text = "✔ ${doc.name}",
                        modifier = Modifier.clickable {
                            PrivatePdfViewer.open(context, documentScope, doc.url)
                        },
                        color = MaterialTheme.colorScheme.primary
                    )
                }


            }
        }

        Spacer(Modifier.height(16.dp))

        if (!isLive) {
            OutlinedTextField(
                value = rejectReason,
                onValueChange = onRejectReasonChange,
                label = { Text("Rejection reason") },
                modifier = Modifier.fillMaxWidth(),
                minLines = 2,
                enabled = !isRejected,
                readOnly = isRejected
            )

            Spacer(Modifier.height(24.dp))

            Button(
                onClick = onForwardToField,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Documents Verified & Forward to Field Officer")
            }

            Spacer(Modifier.height(8.dp))

            if (!isRejected) {
                OutlinedButton(
                    onClick = onReject,
                    modifier = Modifier.fillMaxWidth(),
                    enabled = rejectReason.isNotBlank()
                ) {
                    Text("Reject Listing")
                }
            }
        }
    }
}
