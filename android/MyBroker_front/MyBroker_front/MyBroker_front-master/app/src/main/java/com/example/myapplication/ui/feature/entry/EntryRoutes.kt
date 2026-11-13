package com.example.myapplication.ui.feature.entry

import android.content.Context
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowForward
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.preferencesDataStore
import com.example.myapplication.network.SessionManager
import com.example.myapplication.R
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

private val Context.onboardingStore by preferencesDataStore(name = "onboarding_preferences")
private val ONBOARDING_COMPLETE = booleanPreferencesKey("completed")

private suspend fun isOnboardingComplete(context: Context): Boolean =
    context.onboardingStore.data.first()[ONBOARDING_COMPLETE] ?: false

private suspend fun markOnboardingComplete(context: Context) {
    context.onboardingStore.edit { it[ONBOARDING_COMPLETE] = true }
}

@Composable
fun SplashRoute(onNavigate: (String) -> Unit) {
    val context = LocalContext.current
    LaunchedEffect(Unit) {
        val route = when {
            SessionManager(context.applicationContext).isLoggedIn() -> "home"
            isOnboardingComplete(context) -> "login"
            else -> "onboarding"
        }
        onNavigate(route)
    }
    Box(
        modifier = Modifier.fillMaxSize().background(
            Brush.verticalGradient(
                if (com.example.myapplication.ui.feature.isDarkAppTheme()) {
                    listOf(MaterialTheme.colorScheme.background, MaterialTheme.colorScheme.background)
                } else listOf(Color(0xFFEAF4FF), Color.White, Color(0xFFE9F8F2))
            )
        ),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Image(
                painter = painterResource(R.drawable.logo),
                contentDescription = "MyBrokerr",
                contentScale = ContentScale.Fit,
                modifier = Modifier.width(210.dp).height(140.dp)
            )
        }
    }
}

private data class OnboardingPage(
    val eyebrow: String,
    val title: String,
    val description: String,
    val imageRes: Int
)

private val onboardingPages = listOf(
    OnboardingPage("WELCOME TO MYBROKERR", "Welcome to MyBrokerr", "Your Land. Your Choice. Your MyBrokerr.", R.drawable.onboarding_slide3),
    OnboardingPage("BUY & SELL LAND", "The right land is within reach", "Explore trusted listings as a buyer, or publish your property and connect with the right people.", R.drawable.onboarding_slide2),
    OnboardingPage("SMART LAND MAPS", "Explore every boundary", "See where a property sits, understand its plot boundaries, and explore the land around it.", R.drawable.onboarding_slide1),
    OnboardingPage("VERIFIED PROPERTIES", "Move forward with clarity", "Property details and documents are reviewed to help you make a more informed decision.", R.drawable.onboarding_slide4),
    OnboardingPage("EASY & SECURE PROCESS", "Easy from discovery to deal", "Find a property, connect with its owner, arrange a visit, and move ahead with confidence.", R.drawable.onboarding_slide5)
)

@Composable
fun OnboardingRoute(onComplete: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val pagerState = rememberPagerState(pageCount = { onboardingPages.size })
    val complete: () -> Unit = {
        scope.launch {
            markOnboardingComplete(context)
            onComplete()
        }
        Unit
    }
    BoxWithConstraints(
        modifier = Modifier.fillMaxSize().background(
            Brush.verticalGradient(
                if (com.example.myapplication.ui.feature.isDarkAppTheme()) {
                    listOf(MaterialTheme.colorScheme.background, MaterialTheme.colorScheme.surfaceVariant)
                } else listOf(Color(0xFFF4F9FF), Color.White, Color(0xFFF0FAF5))
            )
        )
    ) {
        val compact = maxHeight < 740.dp
        Column(Modifier.fillMaxSize().padding(horizontal = 24.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Row(Modifier.fillMaxWidth().padding(top = if (compact) 16.dp else 24.dp), verticalAlignment = Alignment.CenterVertically) {
                Image(
                    painter = painterResource(R.drawable.logo),
                    contentDescription = "MyBrokerr",
                    contentScale = ContentScale.Fit,
                    modifier = Modifier.width(96.dp).height(64.dp)
                )
                Spacer(Modifier.weight(1f))
                TextButton(onClick = complete) { Text("Skip", color = MaterialTheme.colorScheme.onSurfaceVariant, fontWeight = FontWeight.SemiBold) }
            }

            HorizontalPager(
                state = pagerState,
                modifier = Modifier.weight(1f).fillMaxWidth(),
                key = { it }
            ) { page ->
                OnboardingPageContent(onboardingPages[page], compact)
            }

            Row(horizontalArrangement = Arrangement.spacedBy(7.dp), verticalAlignment = Alignment.CenterVertically) {
                onboardingPages.indices.forEach { index ->
                    val selected = pagerState.currentPage == index
                    val width = animateFloatAsState(if (selected) 25f else 7f, label = "page-dot").value
                    Box(Modifier.width(width.dp).height(7.dp).clip(CircleShape).background(
                        if (selected) {
                            if (com.example.myapplication.ui.feature.isDarkAppTheme()) MaterialTheme.colorScheme.primary else Color(0xFF1769E8)
                        } else if (com.example.myapplication.ui.feature.isDarkAppTheme()) MaterialTheme.colorScheme.outlineVariant else Color(0xFFD7E2EF)
                    ))
                }
            }
            Spacer(Modifier.height(20.dp))
            Button(
                onClick = {
                    if (pagerState.currentPage == onboardingPages.lastIndex) complete()
                    else scope.launch { pagerState.animateScrollToPage(pagerState.currentPage + 1) }
                },
                modifier = Modifier.fillMaxWidth().height(58.dp).shadow(9.dp, RoundedCornerShape(20.dp), ambientColor = Color(0x33176AE8), spotColor = Color(0x33176AE8)),
                shape = RoundedCornerShape(20.dp),
                colors = ButtonDefaults.buttonColors(containerColor = if (com.example.myapplication.ui.feature.isDarkAppTheme()) MaterialTheme.colorScheme.primary else Color(0xFF1769E8))
            ) {
                Text(if (pagerState.currentPage == onboardingPages.lastIndex) "Get Started" else if (pagerState.currentPage == 0) "Continue" else "Next", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                Spacer(Modifier.width(10.dp))
                Icon(if (pagerState.currentPage == onboardingPages.lastIndex) Icons.Rounded.CheckCircle else Icons.AutoMirrored.Rounded.ArrowForward, contentDescription = null, modifier = Modifier.size(20.dp))
            }
            Spacer(Modifier.height(if (compact) 18.dp else 28.dp))
        }
    }
}

@Composable
private fun OnboardingPageContent(page: OnboardingPage, compact: Boolean) {
    Column(
        Modifier.fillMaxSize().padding(top = if (compact) 6.dp else 14.dp, bottom = 12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        PropertyIllustration(page.imageRes, Modifier.fillMaxWidth().weight(1f, fill = true).padding(vertical = if (compact) 5.dp else 12.dp))
        Text(page.eyebrow, color = if (com.example.myapplication.ui.feature.isDarkAppTheme()) MaterialTheme.colorScheme.secondary else Color(0xFF168C72), fontSize = 11.sp, fontWeight = FontWeight.ExtraBold, letterSpacing = 1.6.sp, textAlign = TextAlign.Center)
        Spacer(Modifier.height(12.dp))
        Text(page.title, color = if (com.example.myapplication.ui.feature.isDarkAppTheme()) MaterialTheme.colorScheme.onBackground else Color(0xFF12345A), fontSize = if (compact) 27.sp else 31.sp, lineHeight = if (compact) 33.sp else 38.sp, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center)
        Spacer(Modifier.height(12.dp))
        Text(page.description, color = if (com.example.myapplication.ui.feature.isDarkAppTheme()) MaterialTheme.colorScheme.onSurfaceVariant else Color(0xFF65778D), fontSize = 15.sp, lineHeight = 23.sp, textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth().padding(horizontal = 7.dp))
        Spacer(Modifier.height(if (compact) 12.dp else 25.dp))
    }
}

@Composable
private fun PropertyIllustration(imageRes: Int, modifier: Modifier = Modifier) {
    Image(
        painter = painterResource(imageRes),
        contentDescription = null,
        contentScale = ContentScale.Fit,
        modifier = modifier
            .clip(RoundedCornerShape(30.dp))
    )
}

