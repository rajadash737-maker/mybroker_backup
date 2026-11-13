package com.example.mybroker_admin.feature.fieldofficer.sitevisit

import android.util.Log
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.navigation.NavController
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.remote.PrivatePdfViewer
import java.util.Locale

@Composable
fun FieldDocumentViewerScreen(
    navController: NavController,
    docUrl: String,
    returnTo: String
) {
    val context = LocalContext.current
    val documentScope = rememberCoroutineScope()

    val fullUrl = ApiClient.absoluteUrl(docUrl) ?: docUrl
    Log.d("FO_DOC_DEBUG", "viewer docUrl=$docUrl fullUrl=$fullUrl")

    val normalized = fullUrl.substringBefore("?").substringBefore("#").lowercase(Locale.US)
    val isPdf = normalized.endsWith(".pdf")

    BackHandler {
        if (!navController.popBackStack(returnTo, false)) {
            navController.popBackStack()
        }
    }

    if (isPdf) {
        LaunchedEffect(fullUrl) {
            PrivatePdfViewer.open(context, documentScope, fullUrl)
        }
        return
    }

    AndroidView(
        modifier = Modifier.fillMaxSize(),
        factory = { ctx ->
            WebView(ctx).apply {
                settings.javaScriptEnabled = true
                settings.domStorageEnabled = true
                webViewClient = WebViewClient()
                loadUrl(fullUrl)
            }
        }
    )
}
