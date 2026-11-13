package com.example.myapplication.ui.feature.home.profile

import android.content.Context
import android.net.Uri
import android.widget.Toast
import com.example.myapplication.network.ApiClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File

object UploadImageToServer {

    suspend fun uploadProfileImage(
        context: Context,
        uri: Uri,
        onSuccess: (String) -> Unit
    ) = withContext(Dispatchers.IO) {
        var tempFile: File? = null

        try {
            val mimeType = context.contentResolver.getType(uri)
                ?.substringBefore(';')
                ?.trim()
                ?.lowercase()
                ?: throw IllegalArgumentException("Cannot determine the selected image format")
            val extension = when (mimeType) {
                "image/jpeg", "image/jpg" -> ".jpg"
                "image/png" -> ".png"
                "image/webp" -> ".webp"
                else -> throw IllegalArgumentException("Unsupported image format: $mimeType")
            }

            val input = context.contentResolver.openInputStream(uri)
                ?: throw IllegalStateException("Cannot read image")
            tempFile = File.createTempFile("profile_", extension, context.cacheDir)

            input.use { ins ->
                tempFile.outputStream().use { out -> ins.copyTo(out) }
            }

            val header = ByteArray(12)
            val headerBytes = tempFile.inputStream().use { it.read(header) }
            val contentMatchesMime = when (mimeType) {
                "image/jpeg", "image/jpg" -> headerBytes >= 3 &&
                    header[0] == 0xFF.toByte() && header[1] == 0xD8.toByte() && header[2] == 0xFF.toByte()
                "image/png" -> headerBytes >= 8 &&
                    header.copyOfRange(0, 8).contentEquals(byteArrayOf(
                        0x89.toByte(), 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A
                    ))
                "image/webp" -> headerBytes >= 12 &&
                    String(header, 0, 4, Charsets.US_ASCII) == "RIFF" &&
                    String(header, 8, 4, Charsets.US_ASCII) == "WEBP"
                else -> false
            }
            if (!contentMatchesMime) {
                throw IllegalArgumentException("Image content does not match its reported format")
            }

            val reqFile = tempFile.asRequestBody(mimeType.toMediaTypeOrNull())
            val filePart = MultipartBody.Part.createFormData("file", tempFile.name, reqFile)

            val response = ApiClient.apiService.uploadProfilePhoto(filePart)

            if (response.isSuccessful) {
                val body = response.body() ?: throw IllegalStateException("Empty response")
                val absolute = ApiClient.absoluteUrl(body.profileImageUrl) ?: body.profileImageUrl
                withContext(Dispatchers.Main) { onSuccess(absolute) }
            } else {
                throw IllegalStateException("Upload failed: ${response.code()}")
            }
        } catch (e: Exception) {
            withContext(Dispatchers.Main) {
                Toast.makeText(context, e.message ?: "Upload failed!", Toast.LENGTH_SHORT).show()
            }
        } finally {
            tempFile?.delete()
        }
    }

}
