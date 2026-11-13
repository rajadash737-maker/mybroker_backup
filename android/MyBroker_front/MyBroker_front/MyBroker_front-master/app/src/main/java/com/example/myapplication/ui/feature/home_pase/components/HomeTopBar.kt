package com.example.myapplication.ui.feature.home_pase.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.HomeWork
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.outlined.FavoriteBorder
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import androidx.compose.ui.unit.dp
import coil.compose.rememberAsyncImagePainter
import com.example.myapplication.R
import com.example.myapplication.network.ApiClient

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeTopBar(
    onNotificationClick: () -> Unit,
    onLikeClick: () -> Unit,      // NEW
    onLandClick: () -> Unit,
    onProfileClick: () -> Unit,
    unreadCount: Int = 0
) {
    val context = LocalContext.current
    val api = remember(context) {
        ApiClient.init(context.applicationContext)
        ApiClient.apiService
    }
    var profileImageUrl by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(Unit) {
        try {
            val res = api.getMyProfile()
            if (res.isSuccessful) {
                val p = res.body()
                profileImageUrl = ApiClient.absoluteUrl(p?.profileImageUrl) ?: p?.profileImageUrl
            }
        } catch (_: Exception) {}
    }

    TopAppBar(
        modifier = Modifier.background(
            Brush.verticalGradient(
                colors = listOf(Color(0xFF0D47A1), Color(0xFF1565C0))
            )
        ),
        colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Transparent),
        title = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(40.dp)
                        .shadow(2.dp, CircleShape)
                        .clip(CircleShape)
                        .background(Color.White),
                    contentAlignment = Alignment.Center
                ) {
                    Image(
                        painter = painterResource(R.drawable.logo),
                        contentDescription = "MyBrokerr logo",
                        modifier = Modifier
                            .size(40.dp)
                            .padding(5.dp),
                        contentScale = ContentScale.Fit
                    )
                }
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    "MyBrokerr",
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                    fontSize = 18.sp,
                    maxLines = 1,
                    softWrap = false
                )
            }
        },
        actions = {
            IconButton(onClick = onNotificationClick) {
                BadgedBox(
                    badge = {
                        if (unreadCount > 0) {
                            Badge {
                                Text(if (unreadCount > 99) "99+" else unreadCount.toString())
                            }
                        }
                    }
                ) {
                    Icon(Icons.Default.Notifications, contentDescription = "Notifications", tint = Color.White)
                }
            }

            IconButton(onClick = onLikeClick) { // NEW like icon
                Icon(Icons.Outlined.FavoriteBorder, contentDescription = "Favorites", tint = Color.White)
            }

            IconButton(onClick = onLandClick) {
                Icon(Icons.Default.HomeWork, contentDescription = "Land", tint = Color.White)
            }

            IconButton(onClick = onProfileClick) {
                val model = if (!profileImageUrl.isNullOrBlank()) profileImageUrl else R.drawable.ic_user
                Image(
                    painter = rememberAsyncImagePainter(model),
                    contentDescription = "Profile",
                    modifier = Modifier
                        .size(32.dp)
                        .clip(CircleShape)
                        .border(2.dp, Color.White, CircleShape)
                )
            }
        }
    )
}
