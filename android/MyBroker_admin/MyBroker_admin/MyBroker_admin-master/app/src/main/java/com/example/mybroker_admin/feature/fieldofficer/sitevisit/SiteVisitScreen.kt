// SiteVisitScreen.kt
package com.example.mybroker_admin.feature.fieldofficer.sitevisit

import android.util.Log
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import coil.compose.SubcomposeAsyncImage
import com.example.mybroker_admin.core.navigation.Routes
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.feature.fieldofficer.sitevisit.components.*
import com.google.android.gms.maps.model.LatLng
import java.math.BigDecimal
import java.text.NumberFormat
import java.util.Locale

@Composable
fun SiteVisitScreen(
    navController: NavController,
    requestId: Int,
    viewModel: SiteVisitViewModel = viewModel()
) {
    val ui by viewModel.uiState.collectAsStateWithLifecycle()
    var notes by remember { mutableStateOf("") }
    var rejectReason by remember { mutableStateOf("") }
    var showRejectField by remember { mutableStateOf(false) }

    LaunchedEffect(requestId) {
        viewModel.loadCaseDetail(requestId)
    }

    LaunchedEffect(ui.detail?.id) {
        val detail = ui.detail ?: return@LaunchedEffect
        val polygonPoints = detail.boundary_points.map { LatLng(it.lat, it.lng) }
        val destination = polygonPoints.firstOrNull() ?: LatLng(26.9124, 75.7873)
        viewModel.startTracking(destination)
    }

    DisposableEffect(Unit) {
        onDispose { viewModel.stopTracking() }
    }

    LaunchedEffect(ui.successMessage) {
        if (!ui.successMessage.isNullOrBlank()) {
            navController.popBackStack(Routes.FIELD_DASHBOARD, false)
            viewModel.clearSuccess()
        }
    }

    if (ui.loading) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        return
    }

    val detail = ui.detail ?: return
    val documents = detail.media.filter { it.media_type.equals("document", ignoreCase = true) }
    val polygonPoints = detail.boundary_points.map { LatLng(it.lat, it.lng) }
    val mapCenter = polygonPoints.firstOrNull() ?: LatLng(26.9124, 75.7873)
    val categoryLabel = sellerCategoryLabel(detail.owner_category)
    val photoUrls = detail.media
        .filter { it.media_type.equals("photo", ignoreCase = true) }
        .mapNotNull { ApiClient.absoluteUrl(it.file_url) ?: it.file_url }
        .map { it.trim() }
        .filter { it.isNotEmpty() }
        .distinct()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
    ) {
        Text("Listing Review", style = MaterialTheme.typography.titleLarge)
        Spacer(modifier = Modifier.height(12.dp))

        if (!ui.error.isNullOrBlank()) {
            Text(ui.error!!, color = MaterialTheme.colorScheme.error)
            Spacer(modifier = Modifier.height(8.dp))
        }

        SellerDetailsCard(
            name = detail.seller.fullname,
            mobile = detail.seller.mobile,
            sellerType = "Owner",
            category = categoryLabel
        )

        LandDetailsCard(
            title = detail.title ?: "-",
            area = formatArea(detail.area, detail.area_unit),
            city = detail.city ?: "-",
            state = detail.state ?: "-",
            price = detail.expected_price?.let { formatPrice(it) } ?: "-"
        )

        if (photoUrls.isNotEmpty()) {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 12.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Land Photos", style = MaterialTheme.typography.titleMedium)
                    Spacer(modifier = Modifier.height(8.dp))
                    LazyRow {
                        items(photoUrls) { url ->
                            SubcomposeAsyncImage(
                                model = url,
                                contentDescription = "Land photo",
                                modifier = Modifier
                                    .size(110.dp)
                                    .padding(end = 8.dp),
                                contentScale = ContentScale.Crop,
                                loading = {
                                    CircularProgressIndicator(
                                        modifier = Modifier.size(18.dp),
                                        strokeWidth = 2.dp
                                    )
                                }
                            )
                        }
                    }
                }
            }
        }

        DocumentSection(
            documents = documents,
            onViewClick = { url ->
                val resolved = ApiClient.absoluteUrl(url) ?: url
                Log.d("FO_DOC_DEBUG", "onView raw=$url resolved=$resolved")

                navController.navigate(
                    Routes.fieldDocumentViewer(
                        docUrl = resolved,
                        returnTo = "listing_review/${detail.id}"
                    )
                )
            }
        )

        SiteMapSection(
            latitude = mapCenter.latitude,
            longitude = mapCenter.longitude,
            polygonPoints = polygonPoints,
            currentLocation = ui.currentLocation,
            routePoints = ui.routePoints
        )

        Spacer(modifier = Modifier.height(16.dp))

        PhotoCaptureSection(
            modifier = Modifier.fillMaxWidth(),
            onPhotoPartReady = { part -> viewModel.uploadVisitPhoto(requestId, part) },
            onError = {}
        )

        if (!ui.photoUploadMessage.isNullOrBlank()) {
            Spacer(modifier = Modifier.height(8.dp))
            Text(ui.photoUploadMessage!!)
        }

        Spacer(modifier = Modifier.height(12.dp))

        OutlinedTextField(
            value = notes,
            onValueChange = { notes = it },
            label = { Text("Inspection Notes") },
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(20.dp))

        Button(
            onClick = { viewModel.approve(requestId, notes) },
            modifier = Modifier.fillMaxWidth(),
            enabled = !ui.submitting
        ) { Text("Approve") }

        Spacer(modifier = Modifier.height(10.dp))

        Button(
            onClick = { showRejectField = true },
            modifier = Modifier.fillMaxWidth(),
            enabled = !ui.submitting,
            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
        ) { Text("Reject") }

        if (showRejectField) {
            Spacer(modifier = Modifier.height(12.dp))
            OutlinedTextField(
                value = rejectReason,
                onValueChange = { rejectReason = it },
                label = { Text("Reject Reason (Required)") },
                modifier = Modifier.fillMaxWidth()
            )
            Spacer(modifier = Modifier.height(10.dp))
            Button(
                onClick = {
                    if (rejectReason.isNotBlank()) {
                        viewModel.reject(requestId, notes, rejectReason)
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                enabled = !ui.submitting,
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
            ) { Text("Confirm Reject") }
        }

        Spacer(modifier = Modifier.height(40.dp))
    }
}

private fun sellerCategoryLabel(raw: String?): String = when (raw?.trim()?.lowercase()) {
    "general" -> "General"
    "obc" -> "OBC"
    "sc" -> "SC"
    "st" -> "ST"
    else -> "-"
}

private fun formatPrice(value: Double): String {
    val formatter = NumberFormat.getNumberInstance(Locale("en", "IN")).apply {
        maximumFractionDigits = 2
    }
    return "Rs ${formatter.format(value)}"
}

private fun formatArea(area: Double?, unit: String?): String {
    if (area == null) return "-".let { value -> if (unit.isNullOrBlank()) value else "$value ${unit.trim()}" }
    val plain = BigDecimal.valueOf(area).stripTrailingZeros().toPlainString()
    val unitText = unit?.trim().orEmpty()
    return if (unitText.isBlank()) plain else "$plain $unitText"
}
