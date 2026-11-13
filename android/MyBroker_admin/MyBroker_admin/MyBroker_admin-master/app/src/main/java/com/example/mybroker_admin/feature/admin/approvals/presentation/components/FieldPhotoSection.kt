package com.example.mybroker_admin.feature.admin.approvals.presentation.components

import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import coil.ImageLoader
import coil.compose.SubcomposeAsyncImage
import coil.imageLoader
import com.example.mybroker_admin.data.remote.ApiClient

private object FieldPhotoImageLoaderProvider {
    @Volatile
    private var authenticatedLoader: ImageLoader? = null

    fun get(context: Context): ImageLoader = authenticatedLoader ?: synchronized(this) {
        authenticatedLoader ?: ImageLoader.Builder(context.applicationContext)
            .okHttpClient { ApiClient.authenticatedMediaOkHttpClient }
            .build()
            .also { authenticatedLoader = it }
    }
}

@Composable
fun FieldPhotoSection(photos: List<String>) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val authenticatedImageLoader = remember(context) {
        FieldPhotoImageLoaderProvider.get(context)
    }

    Column {
        Text("Field Visit Photos")
        Spacer(modifier = Modifier.height(8.dp))

        if (photos.isEmpty()) {
            Text(
                text = "No field visit photo uploaded",
                style = MaterialTheme.typography.bodySmall,
                color = Color.Gray
            )
            return@Column
        }

        LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            items(photos) { photo ->
                SubcomposeAsyncImage(
                    model = photo,
                    imageLoader = if (ApiClient.isTrustedApiUrl(photo)) {
                        authenticatedImageLoader
                    } else {
                        context.imageLoader
                    },
                    contentDescription = "Field visit photo",
                    modifier = Modifier
                        .size(100.dp)
                        .background(Color.LightGray, RoundedCornerShape(8.dp)),
                    contentScale = ContentScale.Crop,
                    loading = {
                        Box(
                            modifier = Modifier.size(100.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            CircularProgressIndicator(strokeWidth = 2.dp)
                        }
                    },
                    error = {
                        Box(
                            modifier = Modifier
                                .size(100.dp)
                                .background(Color.LightGray, RoundedCornerShape(8.dp)),
                            contentAlignment = Alignment.Center
                        ) {
                            Text("Image fail", color = Color.DarkGray)
                        }
                    }
                )
            }
        }
    }
}
