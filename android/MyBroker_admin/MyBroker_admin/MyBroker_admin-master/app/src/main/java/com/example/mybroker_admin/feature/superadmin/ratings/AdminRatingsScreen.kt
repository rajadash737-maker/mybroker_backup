package com.example.mybroker_admin.feature.superadmin.ratings

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.mybroker_admin.data.remote.dto.AdminRatingListItemDto

@Composable
fun AdminRatingsScreen(
    viewModel: AdminRatingsViewModel,
    onBack: () -> Unit
) {
    val state by viewModel.uiState.collectAsState()

    LaunchedEffect(Unit) {
        viewModel.loadRatings()
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF7F5FB))
            .padding(16.dp)
    ) {
        TextButton(onClick = onBack) { Text("Back") }
        Text(
            text = "Ratings Dashboard",
            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold)
        )

        Box(modifier = Modifier.fillMaxSize()) {
            when {
                state.isLoading -> {
                    CircularProgressIndicator(Modifier.align(Alignment.Center))
                }
                !state.errorMessage.isNullOrBlank() -> {
                    Text(
                        text = state.errorMessage ?: "Something went wrong",
                        color = MaterialTheme.colorScheme.error,
                        modifier = Modifier.align(Alignment.Center)
                    )
                }
                state.items.isEmpty() -> {
                    Text(
                        text = "No ratings yet",
                        modifier = Modifier.align(Alignment.Center)
                    )
                }
                else -> {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize().padding(top = 12.dp),
                        contentPadding = PaddingValues(bottom = 16.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        items(state.items) { item ->
                            RatingCard(item)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun RatingCard(item: AdminRatingListItemDto) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Text(
                text = "Property: ${item.propertyTitle ?: "Listing #${item.propertyId}"}",
                style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.SemiBold)
            )
            item.listingCode?.let {
                Text("Code: $it", style = MaterialTheme.typography.bodySmall, color = Color.Gray)
            }
            Text("Role: ${item.role.replace("_", " ").uppercase()}")
            Text("Rating: ${item.rating} / 5")
            if (!item.review.isNullOrBlank()) {
                Text("Review: ${item.review}")
            }
            val fromName = item.fromUser?.fullname ?: "Unknown"
            val toName = item.toUser?.fullname ?: "Unknown"
            Text("From: $fromName  →  To: $toName", style = MaterialTheme.typography.bodySmall)
        }
    }
}
