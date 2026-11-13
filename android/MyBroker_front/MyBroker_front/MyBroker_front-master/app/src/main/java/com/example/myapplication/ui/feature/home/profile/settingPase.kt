package com.example.myapplication.ui.feature.home.profile

import android.content.Context
import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ExitToApp
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.DarkMode
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Feedback
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.StarRate
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.viewModelScope
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.preferencesDataStore
import com.example.myapplication.notification.NotificationPreferences
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch

val LocalThemeViewModel = staticCompositionLocalOf<ThemeViewModel> {
    error("ThemeViewModel not provided")
}

val Context.themeDataStore: DataStore<Preferences> by preferencesDataStore(name = "theme_prefs")

private object ThemePreferencesKeys {
    val DARK_MODE = booleanPreferencesKey("dark_mode_enabled")
}

class ThemeRepository(private val dataStore: DataStore<Preferences>) {
    val isDark: kotlinx.coroutines.flow.Flow<Boolean> =
        dataStore.data.map { it[ThemePreferencesKeys.DARK_MODE] ?: false }

    suspend fun setDark(enabled: Boolean) {
        dataStore.edit { prefs ->
            prefs[ThemePreferencesKeys.DARK_MODE] = enabled
        }
    }
}

class ThemeViewModel(private val repository: ThemeRepository) : ViewModel() {
    private val _isDark = MutableStateFlow(false)
    private var changedByUser = false
    val isDark: StateFlow<Boolean> = _isDark.asStateFlow()

    init {
        viewModelScope.launch {
            repository.isDark.collect { persistedValue ->
                if (!changedByUser) _isDark.value = persistedValue
            }
        }
    }

    fun setDark(enabled: Boolean) {
        changedByUser = true
        _isDark.value = enabled
        viewModelScope.launch { repository.setDark(enabled) }
    }
}

class ThemeViewModelFactory(
    private val repository: ThemeRepository
) : ViewModelProvider.Factory {
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(ThemeViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return ThemeViewModel(repository) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class")
    }
}

class SettingsViewModel : ViewModel()

private const val PRIVACY_POLICY_URL = "https://sites.google.com/view/mybrokerr-privacy/home"
private const val SUPPORT_EMAIL = "mybrokerrofficial@gmail.com"

@Composable
fun SettingsScreen(
    themeViewModel: ThemeViewModel = LocalThemeViewModel.current,
    viewModel: SettingsViewModel = viewModel(),
    onLogoutClick: () -> Unit = {}
) {
    val isDarkTheme by themeViewModel.isDark.collectAsState()
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val notificationsEnabled by NotificationPreferences
        .notificationsEnabledFlow(context.applicationContext)
        .collectAsState(initial = true)
    val selectedLanguageCode by LanguagePreferences
        .selectedLanguageFlow(context.applicationContext)
        .collectAsState(initial = LanguagePreferences.ENGLISH)
    val selectedLanguageLabel = when (selectedLanguageCode) {
        LanguagePreferences.HINDI -> stringResource(id = com.example.myapplication.R.string.language_hindi)
        else -> stringResource(id = com.example.myapplication.R.string.language_english)
    }

    Surface(
        modifier = Modifier
            .fillMaxSize()
            .statusBarsPadding()
            .navigationBarsPadding(),
        color = com.example.myapplication.ui.feature.appBackgroundColor(Color(0xFFF2F5FA))
    ) {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 14.dp),
            verticalArrangement = Arrangement.spacedBy(11.dp)
        ) {

            item { SectionHeader(text = stringResource(id = com.example.myapplication.R.string.settings_general_title)) }

            item {
                ToggleSetting(
                    icon = { Icon(Icons.Default.Notifications, contentDescription = null) },
                    iconTint = Color(0xFF1976D2),
                    iconBackground = Color(0xFFE7F1FF),
                    title = stringResource(id = com.example.myapplication.R.string.settings_notifications),
                    subtitle = stringResource(id = com.example.myapplication.R.string.settings_notifications_subtitle),
                    checked = notificationsEnabled,
                    onCheckedChange = { enabled ->
                        scope.launch {
                            NotificationPreferences.setNotificationsEnabled(
                                context = context.applicationContext,
                                enabled = enabled
                            )
                        }
                    }
                )
            }

            item {
                ToggleSetting(
                    icon = { Icon(Icons.Default.DarkMode, contentDescription = null) },
                    iconTint = Color(0xFF5C6BC0),
                    iconBackground = Color(0xFFEEF0FF),
                    title = stringResource(id = com.example.myapplication.R.string.settings_dark_mode),
                    subtitle = stringResource(id = com.example.myapplication.R.string.settings_dark_mode_subtitle),
                    checked = isDarkTheme,
                    onCheckedChange = { themeViewModel.setDark(it) }
                )
            }

            item {
                DropdownSetting(
                    icon = { Icon(Icons.Default.Language, contentDescription = null) },
                    iconTint = Color(0xFF00897B),
                    iconBackground = Color(0xFFE4F5F1),
                    title = stringResource(id = com.example.myapplication.R.string.settings_language),
                    currentValue = selectedLanguageLabel,
                    options = listOf(
                        LanguageOption(
                            code = LanguagePreferences.ENGLISH,
                            label = stringResource(id = com.example.myapplication.R.string.language_english)
                        ),
                        LanguageOption(
                            code = LanguagePreferences.HINDI,
                            label = stringResource(id = com.example.myapplication.R.string.language_hindi)
                        )
                    ),
                    onSelect = { option ->
                        scope.launch {
                            LanguagePreferences.setLanguage(
                                context = context,
                                languageCode = option.code
                            )
                            (context as? Activity)?.recreate()
                        }
                    }
                )
            }

            item { SectionHeader(text = stringResource(id = com.example.myapplication.R.string.settings_info_title)) }

            item {
                NavigationSetting(
                    icon = { Icon(Icons.Default.StarRate, contentDescription = null) },
                    iconTint = Color(0xFFF59E0B),
                    iconBackground = Color(0xFFFFF4D9),
                    title = stringResource(id = com.example.myapplication.R.string.settings_rate_app),
                    subtitle = stringResource(id = com.example.myapplication.R.string.settings_rate_app_subtitle),
                    onClick = { openRateApp(context) }
                )
            }
            item {
                NavigationSetting(
                    icon = { Icon(Icons.Default.Share, contentDescription = null) },
                    iconTint = Color(0xFF00897B),
                    iconBackground = Color(0xFFE4F5F1),
                    title = stringResource(id = com.example.myapplication.R.string.settings_share_app),
                    subtitle = stringResource(id = com.example.myapplication.R.string.settings_share_app_subtitle),
                    onClick = { shareApp(context) }
                )
            }
            item {
                NavigationSetting(
                    icon = { Icon(Icons.Default.Lock, contentDescription = null) },
                    iconTint = Color(0xFF5C6BC0),
                    iconBackground = Color(0xFFEEF0FF),
                    title = stringResource(id = com.example.myapplication.R.string.settings_privacy_policy),
                    subtitle = stringResource(id = com.example.myapplication.R.string.settings_privacy_policy_subtitle),
                    onClick = { openExternalLink(context, PRIVACY_POLICY_URL) }
                )
            }
            item {
                NavigationSetting(
                    icon = { Icon(Icons.Default.Description, contentDescription = null) },
                    iconTint = Color(0xFF546E7A),
                    iconBackground = Color(0xFFE9EEF1),
                    title = stringResource(id = com.example.myapplication.R.string.settings_terms),
                    subtitle = stringResource(id = com.example.myapplication.R.string.settings_terms_subtitle),
                    onClick = { openExternalLink(context, PRIVACY_POLICY_URL) }
                )
            }
            item {
                NavigationSetting(
                    icon = { Icon(Icons.Default.Email, contentDescription = null) },
                    iconTint = Color(0xFF1976D2),
                    iconBackground = Color(0xFFE7F1FF),
                    title = stringResource(id = com.example.myapplication.R.string.settings_contact_us),
                    subtitle = stringResource(id = com.example.myapplication.R.string.settings_contact_us_subtitle),
                    onClick = {
                        openExternalLink(context, "mailto:$SUPPORT_EMAIL?subject=MyBrokerr%20Support")
                    }
                )
            }
            item {
                NavigationSetting(
                    icon = { Icon(Icons.Default.Feedback, contentDescription = null) },
                    iconTint = Color(0xFFD85B83),
                    iconBackground = Color(0xFFFFECF2),
                    title = stringResource(id = com.example.myapplication.R.string.settings_feedback),
                    subtitle = stringResource(id = com.example.myapplication.R.string.settings_feedback_subtitle),
                    onClick = {
                        openExternalLink(context, "mailto:$SUPPORT_EMAIL?subject=MyBrokerr%20Feedback")
                    }
                )
            }

            item {
                SectionHeader(text = stringResource(id = com.example.myapplication.R.string.logout))
            }

            item {
                Spacer(modifier = Modifier.height(4.dp))
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 3.dp)
                ) {
                    TextButton(
                        onClick = onLogoutClick,
                        modifier = Modifier
                            .fillMaxWidth()
                            .heightIn(min = 58.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(38.dp)
                                .clip(RoundedCornerShape(12.dp))
                                .background(MaterialTheme.colorScheme.errorContainer),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(Icons.AutoMirrored.Filled.ExitToApp, contentDescription = null, tint = MaterialTheme.colorScheme.error)
                        }
                        Spacer(modifier = Modifier.width(12.dp))
                        Text(
                            text = stringResource(id = com.example.myapplication.R.string.logout),
                            color = MaterialTheme.colorScheme.error,
                            fontWeight = FontWeight.SemiBold
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun SectionHeader(text: String) {
    Text(
        text = text,
        style = MaterialTheme.typography.titleMedium,
        fontWeight = FontWeight.SemiBold,
        color = if (com.example.myapplication.ui.feature.isDarkAppTheme()) MaterialTheme.colorScheme.onSurface else Color(0xFF233247),
        modifier = Modifier.padding(start = 4.dp, top = 6.dp, bottom = 1.dp)
    )
}

@Composable
private fun SettingsCard(content: @Composable ColumnScope.() -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 3.dp)
    ) {
        Column(modifier = Modifier.fillMaxWidth(), content = content)
    }
}

@Composable
private fun ToggleSetting(
    icon: @Composable (() -> Unit)? = null,
    iconTint: Color = Color(0xFF1976D2),
    iconBackground: Color = Color(0xFFE7F1FF),
    title: String,
    subtitle: String? = null,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit
) {
    SettingsCard {
        ListItem(
            leadingContent = {
                if (icon != null) SettingsIcon(icon, iconTint, iconBackground)
            },
            headlineContent = { Text(text = title, fontWeight = FontWeight.Medium) },
            supportingContent = {
                if (!subtitle.isNullOrEmpty()) Text(text = subtitle, maxLines = 2)
            },
            trailingContent = {
                Switch(checked = checked, onCheckedChange = onCheckedChange)
            },
            colors = ListItemDefaults.colors(containerColor = Color.Transparent)
        )
    }
}

@Composable
private fun NavigationSetting(
    icon: @Composable (() -> Unit)? = null,
    iconTint: Color = Color(0xFF1976D2),
    iconBackground: Color = Color(0xFFE7F1FF),
    title: String,
    subtitle: String? = null,
    onClick: () -> Unit
) {
    SettingsCard {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clickable { onClick() }
                .padding(horizontal = 16.dp, vertical = 13.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            if (icon != null) {
                SettingsIcon(icon, iconTint, iconBackground)
                Spacer(modifier = Modifier.width(12.dp))
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(text = title, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.Medium)
                if (!subtitle.isNullOrEmpty()) {
                    Text(text = subtitle, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
            Icon(
                Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = if (com.example.myapplication.ui.feature.isDarkAppTheme()) MaterialTheme.colorScheme.onSurfaceVariant else Color(0xFF8A96A6)
            )
        }
    }
}

@Composable
private fun DropdownSetting(
    icon: @Composable (() -> Unit)? = null,
    iconTint: Color = Color(0xFF1976D2),
    iconBackground: Color = Color(0xFFE7F1FF),
    title: String,
    currentValue: String,
    options: List<LanguageOption>,
    onSelect: (LanguageOption) -> Unit
) {
    var expanded by remember { mutableStateOf(false) }
    NavigationSetting(
        icon = icon,
        iconTint = iconTint,
        iconBackground = iconBackground,
        title = title,
        subtitle = currentValue,
        onClick = { expanded = true }
    )
    DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
        options.forEach { opt ->
            DropdownMenuItem(text = { Text(opt.label) }, onClick = {
                onSelect(opt)
                expanded = false
            })
        }
    }
}

@Composable
private fun SettingsIcon(
    icon: @Composable () -> Unit,
    tint: Color,
    background: Color
) {
    val resolvedBackground = com.example.myapplication.ui.feature.appSurfaceColor(background)
    Box(
        modifier = Modifier
            .size(40.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(resolvedBackground),
        contentAlignment = Alignment.Center
    ) {
        CompositionLocalProvider(LocalContentColor provides tint) {
            icon()
        }
    }
}

data class LanguageOption(
    val code: String,
    val label: String
)

private fun openExternalLink(context: Context, rawUrl: String) {
    val normalized = if (
        rawUrl.startsWith("http://", ignoreCase = true) ||
        rawUrl.startsWith("https://", ignoreCase = true) ||
        rawUrl.startsWith("tel:", ignoreCase = true) ||
        rawUrl.startsWith("mailto:", ignoreCase = true)
    ) {
        rawUrl
    } else {
        "https://$rawUrl"
    }

    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(normalized)).apply {
        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    }
    context.startActivity(intent)
}

private fun openRateApp(context: Context) {
    val marketIntent = Intent(
        Intent.ACTION_VIEW,
        Uri.parse("market://details?id=${context.packageName}")
    )
    try {
        context.startActivity(marketIntent)
    } catch (_: Exception) {
        try {
            openExternalLink(
                context,
                "https://play.google.com/store/apps/details?id=${context.packageName}"
            )
        } catch (_: Exception) {
            Toast.makeText(context, "Unable to open the app store.", Toast.LENGTH_SHORT).show()
        }
    }
}

private fun shareApp(context: Context) {
    val shareIntent = Intent(Intent.ACTION_SEND).apply {
        type = "text/plain"
        putExtra(
            Intent.EXTRA_TEXT,
            "Discover MyBrokerr: https://play.google.com/store/apps/details?id=${context.packageName}"
        )
    }
    context.startActivity(Intent.createChooser(shareIntent, "Share MyBrokerr"))
}
//
//@Preview(showBackground = true)
//@Composable
//private fun SettingsScreenPreview() {
//    SettingsScreen()
//}

