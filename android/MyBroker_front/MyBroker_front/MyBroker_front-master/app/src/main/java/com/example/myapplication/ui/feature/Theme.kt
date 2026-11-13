//package com.example.myapplication.ui.theme
package com.example.myapplication.ui.feature

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext
import androidx.compose.material3.Typography
import androidx.compose.ui.graphics.Color

val AppTypography = Typography()

private val DarkColorScheme = darkColorScheme(
    primary = BrokerBlueDark,
    secondary = BrokerGreenDark,
    tertiary = BrokerBlueDark,
    background = BrokerSurfaceDark,
    surface = BrokerSurfaceAltDark,
    surfaceVariant = BrokerSurfaceAltDark,
    onPrimary = Color(0xFF07111C),
    onSecondary = BrokerText,
    onBackground = BrokerTextDark,
    onSurface = BrokerTextDark,
    onSurfaceVariant = BrokerMutedDark,
    outline = BrokerMutedDark
)

private val LightColorScheme = lightColorScheme(
    primary = BrokerBlue,
    secondary = BrokerGreen,
    tertiary = BrokerBlue,
    background = BrokerSurfaceAlt,
    surface = BrokerSurface,
    surfaceVariant = BrokerSky,
    onPrimary = BrokerSurface,
    onSecondary = BrokerSurface,
    onBackground = BrokerText,
    onSurface = BrokerText,
    onSurfaceVariant = BrokerMuted,
    outline = BrokerStroke
)

internal fun appColorScheme(darkTheme: Boolean) =
    if (darkTheme) DarkColorScheme else LightColorScheme

@Composable
internal fun isDarkAppTheme(): Boolean = MaterialTheme.colorScheme.onSurface == BrokerTextDark

@Composable
internal fun appSurfaceColor(lightModeColor: Color): Color =
    if (isDarkAppTheme()) MaterialTheme.colorScheme.surfaceVariant else lightModeColor

@Composable
internal fun appBackgroundColor(lightModeColor: Color): Color =
    if (isDarkAppTheme()) MaterialTheme.colorScheme.background else lightModeColor

@Composable
fun MyApplicationTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context)
            else dynamicLightColorScheme(context)
        }

        else -> appColorScheme(darkTheme)
    }
    MaterialTheme(
        colorScheme = colorScheme,
        typography = AppTypography,
        content = content
    )

}
