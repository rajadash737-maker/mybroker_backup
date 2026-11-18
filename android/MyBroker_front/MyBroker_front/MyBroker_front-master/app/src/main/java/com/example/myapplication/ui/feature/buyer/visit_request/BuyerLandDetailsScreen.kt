package com.example.myapplication.ui.feature.buyer.visit_request

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.myapplication.ui.feature.common.BookingDetailTimelineEvent
import com.example.myapplication.ui.feature.common.BookingPropertyDetails

@Composable
fun BuyerLandDetailsScreen(
    landId: Int,
    viewModel: BuyerLandDetailsViewModel,
    onBack: () -> Unit,
    dealAmount: Double?,
    bookingStatus: String,
    registryDate: String,
    registryTime: String,
    registryLocation: String
) {
    val state by viewModel.uiState.collectAsState()
    LaunchedEffect(landId) { viewModel.load(landId) }

    Column(
        Modifier.fillMaxSize().padding(horizontal = 16.dp).verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("Back", Modifier.clickable(onClick = onBack).padding(top = 12.dp), color = MaterialTheme.colorScheme.primary)
        when {
            state.loading -> Column(
                Modifier.fillMaxWidth().padding(32.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) { CircularProgressIndicator() }
            state.error != null -> Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(state.error.orEmpty(), color = MaterialTheme.colorScheme.error)
                TextButton(onClick = { viewModel.load(landId) }) { Text("Retry") }
            }
            state.land != null -> {
                val land = state.land!!
                val offer = state.offer
                val resolvedStatus = land.bookingStatus?.takeIf(String::isNotBlank)
                    ?: offer?.bookingStatus?.takeIf(String::isNotBlank)
                    ?: bookingStatus
                val acceptedStates = setOf(
                    "accepted_book_now", "booked", "confirmed", "in_process", "registry_scheduled", "registry_done", "sold", "cancelled"
                )
                val bookedStates = acceptedStates - "accepted_book_now"
                val acceptedOfferAmount = offer?.takeIf {
                    it.offerStatus.equals("accepted", ignoreCase = true) || it.bookingStatus in acceptedStates
                }?.finalAmount
                val bookingExists = offer?.bookingId != null || land.bookingStatus != null ||
                    resolvedStatus.trim().lowercase() in bookedStates
                val authoritativeDealAmount = if (bookingExists) {
                    land.dealAmount
                } else {
                    acceptedOfferAmount ?: dealAmount
                }
                val boundaryInfo = when {
                    land.boundaryPoints.isNotEmpty() -> "Boundary available (${land.boundaryPoints.size} points)"
                    !land.mapUrl.isNullOrBlank() -> "Map available"
                    else -> null
                }

                Text(land.title, style = MaterialTheme.typography.headlineSmall)
                BookingPropertyDetails(
                    listingId = land.id,
                    title = land.title,
                    location = land.location,
                    city = land.city,
                    state = land.state,
                    pincode = land.pincode,
                    landType = land.landType,
                    ownerCategory = land.ownerCategory,
                    area = land.area,
                    areaUnit = land.areaUnit,
                    listingStatus = land.listingStatus,
                    bookingStatus = resolvedStatus.ifBlank { null },
                    hasBooking = bookingExists,
                    agreedDealAmount = authoritativeDealAmount,
                    registryDate = land.registryDate?.takeIf(String::isNotBlank) ?: registryDate.ifBlank { null },
                    registryTime = land.registryTime?.takeIf(String::isNotBlank) ?: registryTime.ifBlank { null },
                    registryLocation = land.registryLocation?.takeIf(String::isNotBlank) ?: registryLocation.ifBlank { null },
                    boundaryInformation = boundaryInfo,
                    registryProofs = land.registryProofs.map { it.fileName to it.createdAt },
                    offerEvents = offer?.timeline?.map { BookingDetailTimelineEvent(it.key, it.at) }.orEmpty(),
                    cancellationReason = offer?.cancellationReason,
                    refundDecision = offer?.refundDecision,
                    refundStatus = offer?.refundStatus,
                    refundAmount = offer?.actualRefundedAmount ?: offer?.approvedRefundAmount,
                    refundReference = offer?.refundTransactionReference,
                    refundDate = offer?.refundConfirmedAt
                )
            }
            else -> Text("Land details unavailable")
        }
    }
}
