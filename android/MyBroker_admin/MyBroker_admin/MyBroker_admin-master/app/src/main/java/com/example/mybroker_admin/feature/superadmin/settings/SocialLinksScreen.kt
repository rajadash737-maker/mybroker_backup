package com.example.mybroker_admin.feature.superadmin.settings

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
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
import androidx.lifecycle.viewmodel.compose.viewModel

@Composable
fun SocialLinksScreen(
    onBack: () -> Unit,
    viewModel: SettingsViewModel = viewModel()
) {
    val state by viewModel.uiState.collectAsState()

    LaunchedEffect(Unit) { viewModel.loadLinks() }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF7F5FB))
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        TextButton(onClick = onBack) { Text("Back") }
        Text(
            text = "Social Links",
            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold)
        )
        Text(
            text = "Paste full URLs so the user app can open them directly.",
            style = MaterialTheme.typography.bodySmall,
            color = Color.Gray
        )

        if (state.isLoading) {
            Spacer(modifier = Modifier.height(12.dp))
            CircularProgressIndicator(Modifier.align(Alignment.CenterHorizontally))
        }

        OutlinedTextField(
            value = state.data.whatsapp,
            onValueChange = viewModel::onWhatsappChange,
            label = { Text("WhatsApp") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )

        OutlinedTextField(
            value = state.data.instagram,
            onValueChange = viewModel::onInstagramChange,
            label = { Text("Instagram") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )

        OutlinedTextField(
            value = state.data.telegram,
            onValueChange = viewModel::onTelegramChange,
            label = { Text("Telegram") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )

        OutlinedTextField(
            value = state.data.youtube,
            onValueChange = viewModel::onYoutubeChange,
            label = { Text("YouTube") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )

        OutlinedTextField(
            value = state.data.facebook,
            onValueChange = viewModel::onFacebookChange,
            label = { Text("Facebook") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )

        OutlinedTextField(
            value = state.data.linkedin,
            onValueChange = viewModel::onLinkedinChange,
            label = { Text("LinkedIn") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )

        Button(
            onClick = viewModel::saveLinks,
            enabled = !state.isSaving,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(if (state.isSaving) "Saving..." else "Save Links")
        }

        state.message?.let {
            Text(it, color = MaterialTheme.colorScheme.primary)
        }
    }
}

