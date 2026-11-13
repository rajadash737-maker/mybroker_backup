package com.example.mybroker_admin.data.remote

import android.content.ClipData
import android.content.Context
import android.content.Intent
import android.content.ActivityNotFoundException
import android.widget.Toast
import androidx.core.content.FileProvider
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.IOException
import java.util.UUID

object PrivatePdfViewer {
    fun open(context: Context, scope: CoroutineScope, url: String) {
        scope.launch {
            try {
                val file = withContext(Dispatchers.IO) { downloadToCache(context, url) }
                val contentUri = FileProvider.getUriForFile(
                    context,
                    "${context.packageName}.fileprovider",
                    file
                )
                val viewIntent = Intent(Intent.ACTION_VIEW).apply {
                    setDataAndType(contentUri, "application/pdf")
                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
                    clipData = ClipData.newUri(context.contentResolver, "Private PDF", contentUri)
                }
                if (viewIntent.resolveActivity(context.packageManager) == null) {
                    throw PrivatePdfFailure("No PDF viewer is installed on this device")
                }
                context.startActivity(Intent.createChooser(viewIntent, "Open document"))
            } catch (e: PrivatePdfFailure) {
                showMessage(context, e.message ?: "Could not open this document")
            } catch (_: IOException) {
                showMessage(context, "Network error while downloading the document. Please try again.")
            } catch (_: ActivityNotFoundException) {
                showMessage(context, "No PDF viewer is available to open this document")
            } catch (_: Exception) {
                showMessage(context, "Could not download or open the document. Please try again.")
            }
        }
    }

    private suspend fun downloadToCache(context: Context, url: String): File {
        val response = ApiClient.downloadPrivatePdf(url)
        if (!response.isSuccessful) {
            response.errorBody()?.close()
            val message = when (response.code()) {
                401 -> "Your session has expired. Sign in again to view this document."
                403 -> "You do not have permission to view this document."
                404 -> "This document could not be found."
                else -> "Document download failed (HTTP ${response.code()})."
            }
            throw PrivatePdfFailure(message)
        }

        val body = response.body() ?: throw PrivatePdfFailure("The server returned an empty document")
        val cacheDirectory = File(context.cacheDir, "private_documents")
        if (!cacheDirectory.exists() && !cacheDirectory.mkdirs()) {
            throw PrivatePdfFailure("Could not prepare private document storage")
        }
        val file = File(cacheDirectory, "${UUID.randomUUID()}.pdf")

        try {
            body.use { responseBody ->
                responseBody.byteStream().use { input ->
                    file.outputStream().use { output -> input.copyTo(output) }
                }
            }
            val signature = ByteArray(5)
            val signatureLength = file.inputStream().use { it.read(signature) }
            if (signatureLength != signature.size ||
                !signature.contentEquals("%PDF-".toByteArray(Charsets.US_ASCII))
            ) {
                throw PrivatePdfFailure("The server response is not a valid PDF")
            }
            return file
        } catch (e: Exception) {
            file.delete()
            throw e
        }
    }

    private fun showMessage(context: Context, message: String) {
        Toast.makeText(context, message, Toast.LENGTH_LONG).show()
    }

    private class PrivatePdfFailure(message: String) : IOException(message)
}
