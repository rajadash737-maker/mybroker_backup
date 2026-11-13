package com.example.myapplication.ui.feature.buyer.explore.components

import android.util.Log
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.Map
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import coil.compose.AsyncImage
import coil.request.ImageRequest
import com.example.myapplication.network.ApiClient
import com.example.myapplication.ui.feature.buyer.explore.Land
import com.example.myapplication.ui.feature.buyer.explore.WishlistHeartStyle
import com.example.myapplication.ui.feature.buyer.utils.formatAreaWithUnit
import com.example.myapplication.ui.feature.buyer.utils.validatedInstagramUrl
import com.example.myapplication.ui.feature.buyer.explore.wishlistCardPresentation
import java.text.NumberFormat
import java.time.Duration
import java.time.OffsetDateTime
import java.time.format.DateTimeParseException
import java.util.Locale

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun LandCard(
    land: Land,
    onClick: () -> Unit,
    onWishlistClick: () -> Unit,
    onMakeOfferClick: () -> Unit,
    onMapClick: () -> Unit
) {
    val context = LocalContext.current

    val imageList = remember(land.images) {
        land.images
            .mapNotNull { raw -> ApiClient.absoluteUrl(raw)?.trim() }
            .filter { it.isNotBlank() }
            .ifEmpty { listOf("https://via.placeholder.com/800x500?text=No+Image") }
    }

    val isLocked = land.isOfferLocked
    val lockTimeText = formatLockRemaining(land.offerLockExpiresAt)
    val wishlistPresentation = land.wishlistCardPresentation()

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(12.dp),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (isLocked) com.example.myapplication.ui.feature.appSurfaceColor(Color(0xFFF5F5F5)) else MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(6.dp)
    ) {
        Column {
            Box {
                val pagerState = rememberPagerState(pageCount = { imageList.size })

                HorizontalPager(
                    state = pagerState,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(220.dp)
                ) { page ->
                    val imageUrl = imageList[page]
                    AsyncImage(
                        model = ImageRequest.Builder(context)
                            .data(imageUrl)
                            .crossfade(true)
                            .listener(
                                onError = { _, result ->
                                    Log.e("LandCard", "Image failed: $imageUrl", result.throwable)
                                }
                            )
                            .build(),
                        contentDescription = null,
                        modifier = Modifier.fillMaxSize(),
                        contentScale = ContentScale.Crop
                    )
                }

                if (land.isVerified) {
                    Text(
                        text = "VERIFIED",
                        color = Color.White,
                        modifier = Modifier
                            .padding(8.dp)
                            .background(Color(0xFF2E7D32), RoundedCornerShape(6.dp))
                            .padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }

                if (isLocked) {
                    Text(
                        text = "LOCKED",
                        color = Color.White,
                        modifier = Modifier
                            .padding(start = 8.dp, top = 42.dp)
                            .background(Color(0xFFD32F2F), RoundedCornerShape(6.dp))
                            .padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }

                Column(
                    modifier = Modifier.align(Alignment.TopEnd).padding(8.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Box(
                        modifier = Modifier
                            .background(Color.White.copy(alpha = 0.96f), CircleShape)
                            .padding(2.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        IconButton(
                            onClick = onWishlistClick,
                            enabled = !land.isLikeUpdating,
                            modifier = Modifier.size(44.dp).semantics {
                                contentDescription = if (land.isLiked) "Unlike listing" else "Like listing"
                            }
                        ) {
                            if (land.isLikeUpdating) {
                                CircularProgressIndicator(modifier = Modifier.size(22.dp), strokeWidth = 2.dp)
                            } else {
                                Icon(
                                    imageVector = if (wishlistPresentation.heartStyle == WishlistHeartStyle.FILLED)
                                        Icons.Default.Favorite else Icons.Default.FavoriteBorder,
                                    contentDescription = null,
                                    modifier = Modifier.size(28.dp),
                                    tint = if (land.isLiked) Color(0xFFE53935) else Color(0xFF424242)
                                )
                            }
                        }
                    }
                    wishlistPresentation.countLabel?.let { count ->
                        Text(
                            text = count,
                            modifier = Modifier
                                .padding(top = 4.dp)
                                .background(Color.White.copy(alpha = 0.96f), RoundedCornerShape(50.dp))
                                .padding(horizontal = 10.dp, vertical = 3.dp),
                            color = Color(0xFF212121),
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }

            }

            Column(modifier = Modifier.padding(12.dp)) {
                val isPerUnitPrice = land.priceType.equals("price_per_unit", ignoreCase = true)
                val priceLabel = when {
                    isPerUnitPrice -> "Price per ${priceUnitLabel(land.areaUnit)}"
                    land.priceType.equals("total_price", ignoreCase = true) -> "Total Land Price"
                    else -> "Listed Price"
                }
                Text(
                    text = priceLabel,
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = formatPrice(land.price),
                    color = Color(0xFF1769D2),
                    fontSize = 24.sp,
                    lineHeight = 30.sp,
                    fontWeight = FontWeight.Bold
                )

                Spacer(modifier = Modifier.height(10.dp))

                Text(
                    text = land.title.ifBlank { "Untitled Land" },
                    style = MaterialTheme.typography.titleMedium
                )

                Text(
                    text = land.displayAddress,
                    style = MaterialTheme.typography.bodyMedium
                )

                Text(
                    text = formatAreaWithUnit(land.area, land.areaUnit),
                    style = MaterialTheme.typography.bodyMedium
                )

                land.pincode?.takeIf { it.isNotBlank() }?.let {
                    Text(
                        text = "Pincode: $it",
                        style = MaterialTheme.typography.bodySmall
                    )
                }

                if (isLocked) {
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = lockTimeText ?: "Temporarily locked",
                        style = MaterialTheme.typography.bodySmall,
                        color = Color(0xFFD32F2F)
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                validatedInstagramUrl(land.instagramUrl)?.let { instagramUrl ->
                    TextButton(
                        modifier = Modifier.fillMaxWidth(),
                        onClick = {
                            runCatching {
                                context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(instagramUrl)))
                            }.onFailure {
                                Toast.makeText(context, "No app or browser can open this Instagram link.", Toast.LENGTH_SHORT).show()
                            }
                        }
                    ) { Text("Instagram") }
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedButton(
                        modifier = Modifier.weight(1f),
                        onClick = onClick
                    ) {
                        Text("Details")
                    }

                    OutlinedButton(
                        modifier = Modifier.weight(1f),
                        onClick = onMapClick
                    ) {
                        Icon(Icons.Default.Map, contentDescription = null)
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Map")
                    }

                    Button(
                        modifier = Modifier.weight(1f),
                        enabled = !isLocked,
                        onClick = onMakeOfferClick
                    ) {
                        Text(if (isLocked) "Locked" else "Offer")
                    }
                }
            }
        }
    }
}

private fun formatPrice(price: Double): String {
    return NumberFormat.getCurrencyInstance(Locale("en", "IN")).apply {
        minimumFractionDigits = 0
        maximumFractionDigits = 2
    }.format(price)
}

private fun priceUnitLabel(areaUnit: String): String = when (
    areaUnit.trim().lowercase(Locale.ROOT).replace(" ", "").replace(".", "")
) {
    "sqft", "squarefoot", "squarefeet" -> "Sq.ft"
    "sqm", "squaremeter", "squaremeters" -> "Sq.m"
    "decimal", "decimals" -> "Decimal"
    "acre", "acres" -> "Acre"
    "hectare", "hectares" -> "Hectare"
    "bigha" -> "Bigha"
    else -> areaUnit.ifBlank { "unit" }
}

private fun formatLockRemaining(expiresAt: String?): String? {
    if (expiresAt.isNullOrBlank()) return null
    return try {
        val expiry = OffsetDateTime.parse(expiresAt).toInstant()
        val now = java.time.Instant.now()
        val duration = Duration.between(now, expiry)
        if (duration.isNegative || duration.isZero) {
            "Lock expired"
        } else {
            val hours = duration.toHours()
            val minutes = duration.toMinutes() % 60
            "Locked for ${hours}h ${minutes}m"
        }
    } catch (_: DateTimeParseException) {
        "Temporarily locked"
    }
}
