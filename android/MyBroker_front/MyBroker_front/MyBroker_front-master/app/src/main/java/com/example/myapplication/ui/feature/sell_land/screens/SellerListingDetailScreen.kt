package com.example.myapplication.ui.feature.sell_land.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.example.myapplication.network.ApiClient
import com.example.myapplication.ui.feature.common.BookingDetailTimelineEvent
import com.example.myapplication.ui.feature.common.BookingPropertyDetails
import com.example.myapplication.ui.feature.sell_land.model.SellLandResponse
import com.example.myapplication.ui.feature.sell_land.model.SellLandTrackingCardResponse
import com.example.myapplication.ui.feature.sell_land.model.SellerOfferItemResponse
import com.example.myapplication.ui.feature.sell_land.viewmodel.SellLandViewModel

@Composable
fun SellerListingDetailScreen(listingId: String, viewModel: SellLandViewModel, onBack: () -> Unit) {
    val context = LocalContext.current
    var listing by remember { mutableStateOf<SellLandResponse?>(null) }
    var tracking by remember { mutableStateOf<SellLandTrackingCardResponse?>(null) }
    var acceptedOffer by remember { mutableStateOf<SellerOfferItemResponse?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var loading by remember { mutableStateOf(true) }
    var retryKey by remember { mutableIntStateOf(0) }

    LaunchedEffect(listingId, retryKey) {
        loading = true
        error = null
        val id = listingId.toIntOrNull()
        if (id == null) {
            error = "Invalid listing ID"
            listing = null
            tracking = null
            acceptedOffer = null
            loading = false
            return@LaunchedEffect
        }

        ApiClient.init(context.applicationContext)
        runCatching {
            val response = ApiClient.apiService.getListingDetails(id)
            if (!response.isSuccessful) throw IllegalStateException("Unable to load listing (${response.code()})")
            response.body() ?: throw IllegalStateException("Listing details were empty")
        }.onSuccess { listing = it }
            .onFailure {
                listing = null
                error = it.message ?: "Unable to load listing"
            }

        runCatching {
            val response = ApiClient.apiService.getMyListingsTracking()
            if (!response.isSuccessful) throw IllegalStateException("Tracking unavailable (${response.code()})")
            response.body()?.firstOrNull { it.id == id }
        }.onSuccess { tracking = it }
            .onFailure { tracking = null }

        runCatching {
            val response = ApiClient.apiService.getListingOffers(id)
            if (!response.isSuccessful) throw IllegalStateException("Offer history unavailable (${response.code()})")
            response.body()?.items
                ?.filter { it.offerStatus.equals("accepted", ignoreCase = true) }
                ?.maxByOrNull { it.sellerResponseAt ?: it.createdAt }
        }.onSuccess { acceptedOffer = it }
            .onFailure { acceptedOffer = null }
        loading = false
    }

    Column(
        Modifier.fillMaxSize().padding(horizontal = 16.dp).verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("Back", Modifier.clickable(onClick = onBack).padding(top = 12.dp), color = MaterialTheme.colorScheme.primary)
        when {
            loading -> Column(
                Modifier.fillMaxSize().padding(32.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) { CircularProgressIndicator() }
            error != null -> Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(error.orEmpty(), color = MaterialTheme.colorScheme.error)
                TextButton(onClick = { retryKey++ }) { Text("Retry") }
            }
            listing != null -> {
                val item = listing!!
                val bookingStatus = tracking?.bookingStatus ?: item.bookingStatus
                val bookingExists = tracking?.bookingStatus != null || item.bookingStatus != null ||
                    tracking?.dealAmount != null || item.dealAmount != null
                val agreedDeal = if (bookingExists) {
                    tracking?.dealAmount ?: item.dealAmount
                } else {
                    acceptedOffer?.let { it.counterAmount ?: it.offeredAmount }
                }
                val offerEvents = acceptedOffer?.let { offer ->
                    buildList {
                        add(BookingDetailTimelineEvent("offer_placed", offer.createdAt))
                        offer.sellerResponseAt?.let { add(BookingDetailTimelineEvent("seller_accepted", it)) }
                    }
                }.orEmpty()
                val boundaryInfo = item.boundaryPoints?.takeIf(String::isNotBlank)?.let { "Boundary information available" }

                Text(item.title ?: "Land listing", style = MaterialTheme.typography.headlineSmall)
                BookingPropertyDetails(
                    listingId = item.id,
                    title = item.title,
                    location = item.location,
                    city = item.city,
                    state = item.state,
                    pincode = item.pincode,
                    landType = item.landType,
                    ownershipType = item.ownershipType,
                    ownerCategory = item.ownerCategory,
                    description = item.description,
                    area = item.area,
                    areaUnit = item.areaUnit,
                    listingStatus = item.status,
                    bookingStatus = bookingStatus,
                    hasBooking = bookingExists,
                    agreedDealAmount = agreedDeal,
                    registryDate = tracking?.registryDate ?: item.registryDate,
                    registryTime = tracking?.registryTime ?: item.registryTime,
                    registryLocation = tracking?.registryLocation ?: item.registryLocation,
                    boundaryInformation = boundaryInfo,
                    registryProofs = tracking?.registryProofs?.map { it.fileName to it.createdAt }.orEmpty(),
                    offerEvents = offerEvents
                )
            }
            else -> Text("Listing details unavailable")
        }
    }
}
