package com.example.myapplication.ui.feature.home.profile

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.DarkMode
import androidx.compose.material.icons.filled.Facebook
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Logout
import androidx.compose.material.icons.filled.Map
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Receipt
import androidx.compose.material.icons.filled.Send
import androidx.compose.material.icons.filled.Work
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import coil.compose.SubcomposeAsyncImage
import com.example.myapplication.R
import com.example.myapplication.network.ApiClient
import com.example.myapplication.network.SocialLinksResponse
import com.example.myapplication.ui.feature.common.NoInternetContent
import com.example.myapplication.ui.feature.common.rememberIsConnected
import com.example.myapplication.ui.feature.ratings.RatingViewModel
import com.example.myapplication.ui.feature.ratings.RatingViewModelFactory
import com.example.myapplication.ui.feature.home_pase.components.LandTypeDialog
import com.example.myapplication.notification.NotificationPreferences

private const val PRIVACY_POLICY_URL = "https://sites.google.com/view/mybrokerr-privacy/home"

@Composable
fun ProfileScreen(
    onEditClick: () -> Unit = {},
    onLogoutClick: () -> Unit = {},
    onMyListedSellerClick: () -> Unit = {},
    onMyListedBuyerClick: () -> Unit = {},

    onMyBookmarkedClick: () -> Unit = {},
    onMapPreferencesClick: () -> Unit = {},
    onMyTransactionsClick: () -> Unit = {},
    onNotificationsClick: () -> Unit = {},
    onLanguageClick: () -> Unit = {}
) {
    val scroll = rememberScrollState()
    val context = LocalContext.current
    val isConnected by rememberIsConnected()
    var retryTick by remember { mutableStateOf(0) }
    val themeViewModel = LocalThemeViewModel.current
    val isDarkMode by themeViewModel.isDark.collectAsState()
    val notificationsEnabled by NotificationPreferences
        .notificationsEnabledFlow(context.applicationContext)
        .collectAsState(initial = true)
    val languageCode by LanguagePreferences
        .selectedLanguageFlow(context.applicationContext)
        .collectAsState(initial = LanguagePreferences.ENGLISH)
    val languageLabel = stringResource(
        id = if (languageCode == LanguagePreferences.HINDI) R.string.language_hindi
        else R.string.language_english
    )

    val api = remember(context) {
        ApiClient.init(context.applicationContext)
        ApiClient.apiService
    }
    val ratingViewModel: RatingViewModel = androidx.lifecycle.viewmodel.compose.viewModel(
        factory = RatingViewModelFactory(context)
    )
    val ratingState by ratingViewModel.uiState.collectAsState()

    var userName by remember { mutableStateOf("User") }
    var userEmail by remember { mutableStateOf("user@example.com") }
    var serverImage by remember { mutableStateOf<String?>(null) }
    var socialLinks by remember { mutableStateOf(SocialLinksResponse(id = 0)) }
    var showLandTypeDialog by remember { mutableStateOf(false) }

    if (!isConnected) {
        NoInternetContent(
            onRetry = { retryTick++ },
            modifier = Modifier.fillMaxSize()
        )
        return
    }

    LaunchedEffect(isConnected, retryTick) {
        if (!isConnected) return@LaunchedEffect
        try {
            val res = api.getMyProfile()
            if (res.isSuccessful) {
                res.body()?.let { p ->
                    userName = p.fullname ?: "User"
                    userEmail = p.email ?: "user@example.com"
                    serverImage = ApiClient.absoluteUrl(p.profileImageUrl?.trim())
                }
            }
        } catch (_: Exception) {
        }
        try {
            val res = api.getSocialLinks()
            if (res.isSuccessful) {
                res.body()?.let { socialLinks = it }
            }
        } catch (_: Exception) {
        }
        ratingViewModel.loadSummaryForCurrentUser()
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(scroll)
            .background(MaterialTheme.colorScheme.background)
            .padding(horizontal = 16.dp, vertical = 12.dp)
    ) {
        if (showLandTypeDialog) {
            LandTypeDialog(
                onDismiss = { showLandTypeDialog = false },
                onSeller = {
                    showLandTypeDialog = false
                    onMyListedSellerClick()
                },
                onBuyer = {
                    showLandTypeDialog = false
                    onMyListedBuyerClick()
                }
            )
        }

        BoxHeader(
            userName = userName,
            userEmail = userEmail,
            serverImage = serverImage,
            onEditClick = onEditClick,
            ratingAverage = ratingState.summaryAverage,
            ratingCount = ratingState.summaryCount
        )

        Spacer(modifier = Modifier.height(20.dp))

        SectionTitle(text = stringResource(id = R.string.profile_my_activities))
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            ProfileOption(
                icon = Icons.Default.LocationOn,
                title = stringResource(id = R.string.profile_my_listed_lands),
                iconTint = MaterialTheme.colorScheme.primary,
                onClick = { showLandTypeDialog = true }
            )
            ProfileOption(
                icon = Icons.Default.Favorite,
                title = stringResource(id = R.string.profile_my_bookmarked_lands),
                iconTint = Color(0xFFD85B83),
                onClick = { onMyBookmarkedClick() }
            )
            ProfileOption(
                icon = Icons.Default.Receipt,
                title = stringResource(id = R.string.profile_my_transactions),
                iconTint = Color(0xFF00897B),
                onClick = { onMyTransactionsClick() }
            )
            ProfileOption(
                icon = Icons.Default.Map,
                title = stringResource(id = R.string.profile_map_preferences),
                iconTint = Color(0xFF5C6BC0),
                onClick = { onMapPreferencesClick() }
            )
        }

        Spacer(modifier = Modifier.height(18.dp))

        SectionTitle(text = stringResource(id = R.string.profile_app_settings))
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            ProfileOption(
                icon = Icons.Default.Notifications,
                title = stringResource(id = R.string.settings_notifications),
                subtitle = if (notificationsEnabled) "Enabled" else "Disabled",
                iconTint = Color(0xFF1976D2),
                onClick = { onNotificationsClick() }
            )
            ProfileOption(
                icon = Icons.Default.DarkMode,
                title = stringResource(id = R.string.settings_dark_mode),
                subtitle = if (isDarkMode) "On" else "Off",
                iconTint = Color(0xFF5C6BC0),
                onClick = { themeViewModel.setDark(!isDarkMode) },
                trailingContent = {
                    Switch(
                        checked = isDarkMode,
                        onCheckedChange = themeViewModel::setDark
                    )
                }
            )
            ProfileOption(
                icon = Icons.Default.Language,
                title = stringResource(id = R.string.settings_language),
                subtitle = languageLabel,
                iconTint = Color(0xFF00897B),
                onClick = { onLanguageClick() }
            )
            ProfileOption(
                icon = Icons.Default.Info,
                title = stringResource(id = R.string.settings_privacy_policy),
                subtitle = "How we protect your information",
                iconTint = Color(0xFF546E7A),
                onClick = { openExternalLink(context, PRIVACY_POLICY_URL) }
            )
        }

        Spacer(modifier = Modifier.height(18.dp))

        SectionTitle(text = stringResource(id = R.string.profile_follow_us))
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            SocialLinkOption(
                icon = Icons.Default.Phone,
                title = stringResource(id = R.string.social_whatsapp),
                url = socialLinks.whatsapp,
                context = context,
                iconTint = Color(0xFF25A366)
            )
            SocialLinkOption(
                icon = Icons.Default.CameraAlt,
                title = stringResource(id = R.string.social_instagram),
                url = socialLinks.instagram,
                context = context,
                iconTint = Color(0xFFC13584)
            )
            SocialLinkOption(
                icon = Icons.Default.Send,
                title = stringResource(id = R.string.social_telegram),
                url = socialLinks.telegram,
                context = context,
                iconTint = Color(0xFF229ED9)
            )
            SocialLinkOption(
                icon = Icons.Default.PlayArrow,
                title = stringResource(id = R.string.social_youtube),
                url = socialLinks.youtube,
                context = context,
                iconTint = Color(0xFFE53935)
            )
            SocialLinkOption(
                icon = Icons.Default.Facebook,
                title = stringResource(id = R.string.social_facebook),
                url = socialLinks.facebook,
                context = context,
                iconTint = Color(0xFF1877F2)
            )
            SocialLinkOption(
                icon = Icons.Default.Work,
                title = stringResource(id = R.string.social_linkedin),
                url = socialLinks.linkedin,
                context = context,
                iconTint = Color(0xFF0A66C2)
            )
        }

        Spacer(modifier = Modifier.height(18.dp))

        ProfileOption(
            icon = Icons.Default.Logout,
            title = stringResource(id = R.string.logout),
            iconTint = MaterialTheme.colorScheme.error,
            onClick = {
                logoutUser(context)
                onLogoutClick()
            }
        )
    }
}

@Composable
private fun BoxHeader(
    userName: String,
    userEmail: String,
    serverImage: String?,
    onEditClick: () -> Unit,
    ratingAverage: Double,
    ratingCount: Int
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 3.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(80.dp)
                    .shadow(4.dp, CircleShape)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.surface)
                    .border(1.5.dp, MaterialTheme.colorScheme.primary, CircleShape)
                    .padding(3.dp)
            ) {
                if (!serverImage.isNullOrBlank()) {
                    SubcomposeAsyncImage(
                        model = serverImage,
                        contentDescription = "Profile Photo",
                        modifier = Modifier
                            .fillMaxSize()
                            .clip(CircleShape),
                        contentScale = ContentScale.Crop,
                        loading = {
                            CircularProgressIndicator(strokeWidth = 2.dp)
                        },
                        error = {
                            Image(
                                painter = painterResource(id = R.drawable.ic_user),
                                contentDescription = "Profile Photo",
                                modifier = Modifier
                                    .fillMaxSize()
                                    .clip(CircleShape)
                            )
                        }
                    )
                } else {
                    Image(
                        painter = painterResource(id = R.drawable.ic_user),
                        contentDescription = "Profile Photo",
                        modifier = Modifier
                            .fillMaxSize()
                            .clip(CircleShape)
                    )
                }
            }

            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = userName,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Text(
                    text = userEmail,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                val avgText = if (ratingCount > 0) String.format("%.1f", ratingAverage) else "0.0"
                Text(
                    text = stringResource(id = R.string.profile_rating_summary, avgText, ratingCount),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.primary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Spacer(modifier = Modifier.height(8.dp))
                Button(
                    onClick = onEditClick,
                    modifier = Modifier.heightIn(min = 36.dp),
                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.primary
                    )
                ) {
                    Text(
                        text = stringResource(id = R.string.profile_edit_profile),
                        style = MaterialTheme.typography.labelLarge
                    )
                }
            }
        }
    }
}

@Composable
fun ProfileOption(
    icon: ImageVector,
    title: String,
    subtitle: String? = null,
    onClick: () -> Unit = {},
    enabled: Boolean = true,
    iconTint: Color = MaterialTheme.colorScheme.primary,
    compact: Boolean = false,
    trailingContent: (@Composable () -> Unit)? = null
) {
    val contentColor = if (enabled) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(enabled = enabled) { onClick() },
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = if (compact) 54.dp else 66.dp)
                .padding(horizontal = 14.dp, vertical = if (compact) 9.dp else 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(if (compact) 36.dp else 40.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(iconTint.copy(alpha = if (enabled) 0.12f else 0.07f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    icon,
                    contentDescription = title,
                    modifier = Modifier.size(if (compact) 20.dp else 22.dp),
                    tint = if (enabled) iconTint else MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = title,
                    style = MaterialTheme.typography.bodyLarge,
                    color = contentColor,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                if (!subtitle.isNullOrBlank()) {
                    Text(
                        text = subtitle,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }
            if (trailingContent != null) {
                trailingContent()
            } else if (enabled) {
                Icon(
                    Icons.AutoMirrored.Filled.KeyboardArrowRight,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun SectionTitle(text: String) {
    Text(
        text = text,
        style = MaterialTheme.typography.titleSmall,
        fontWeight = FontWeight.SemiBold,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp)
    )
}

@Composable
fun SocialLinkOption(
    icon: ImageVector,
    title: String,
    url: String?,
    context: Context,
    iconTint: Color = MaterialTheme.colorScheme.primary
) {
    val link = url?.trim().orEmpty()
    val enabled = link.isNotEmpty()
    ProfileOption(
        icon = icon,
        title = title,
        enabled = enabled,
        iconTint = iconTint,
        compact = true,
        onClick = {
            if (enabled) {
                openExternalLink(context, link)
            }
        }
    )
}

private fun openExternalLink(context: Context, rawUrl: String) {
    val normalized = if (
        rawUrl.startsWith("http://", ignoreCase = true) ||
        rawUrl.startsWith("https://", ignoreCase = true) ||
        rawUrl.startsWith("tel:", ignoreCase = true) ||
        rawUrl.startsWith("mailto:", ignoreCase = true) ||
        rawUrl.startsWith("tg://", ignoreCase = true) ||
        rawUrl.startsWith("whatsapp://", ignoreCase = true)
    ) {
        rawUrl
    } else {
        "https://$rawUrl"
    }

    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(normalized))
    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    context.startActivity(intent)
}

fun logoutUser(context: Context) {
    val prefs = context.getSharedPreferences("user", Context.MODE_PRIVATE)
    prefs.edit().clear().apply()
}

