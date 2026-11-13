package com.example.mybroker_admin.feature.fieldofficer.sitevisit.components

import android.graphics.Bitmap
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File
import java.io.FileOutputStream

@Composable
fun PhotoCaptureSection(
    modifier: Modifier = Modifier,
    onPhotoPartReady: (MultipartBody.Part) -> Unit,
    onError: (String) -> Unit = {}
) {
    val context = LocalContext.current

    val cameraLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.TakePicturePreview()
    ) { bitmap: Bitmap? ->
        if (bitmap == null) {
            onError("Photo capture cancelled")
            return@rememberLauncherForActivityResult
        }

        try {
            val file = File(context.cacheDir, "visit_${System.currentTimeMillis()}.jpg")
            FileOutputStream(file).use { out ->
                bitmap.compress(Bitmap.CompressFormat.JPEG, 90, out)
            }

            val requestBody = file.asRequestBody("image/jpeg".toMediaType())
            val part = MultipartBody.Part.createFormData("file", file.name, requestBody)
            onPhotoPartReady(part)
        } catch (e: Exception) {
            onError(e.message ?: "Failed to prepare photo")
        }
    }

    Button(
        onClick = { cameraLauncher.launch(null) },
        modifier = modifier
    ) {
        Text("Capture Photo")
    }
}
