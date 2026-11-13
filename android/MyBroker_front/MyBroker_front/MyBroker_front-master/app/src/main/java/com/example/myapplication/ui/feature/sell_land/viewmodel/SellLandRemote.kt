package com.example.myapplication.ui.feature.sell_land.viewmodel

import android.content.ContentResolver
import android.net.Uri
import android.provider.OpenableColumns
import com.example.myapplication.network.ApiClient
import com.example.myapplication.ui.feature.sell_land.model.BoundaryPoint
import com.example.myapplication.ui.feature.sell_land.model.BoundaryRequest
import com.example.myapplication.ui.feature.sell_land.model.CancelListingRequest
import com.example.myapplication.ui.feature.sell_land.model.CancelListingResponse
import com.example.myapplication.ui.feature.sell_land.model.CounterOfferRequest
import com.example.myapplication.ui.feature.sell_land.model.DocumentRequirementsResponse
import com.example.myapplication.ui.feature.sell_land.model.PaymentInitRequest
import com.example.myapplication.ui.feature.sell_land.model.PaymentMarkPaidRequest
import com.example.myapplication.ui.feature.sell_land.model.PaymentResponse
import com.example.myapplication.ui.feature.sell_land.model.SellLandRazorpayOrderRequest
import com.example.myapplication.ui.feature.sell_land.model.SellLandRazorpayOrderResponse
import com.example.myapplication.ui.feature.sell_land.model.SellLandRazorpayVerifyRequest
import com.example.myapplication.ui.feature.sell_land.model.SellLandRazorpayVerifyResponse
import com.example.myapplication.ui.feature.sell_land.model.SellLandMediaResponse
import com.example.myapplication.ui.feature.sell_land.model.SellLandResponse
import com.example.myapplication.ui.feature.sell_land.model.SellLandTrackingCardResponse
import com.example.myapplication.ui.feature.sell_land.model.SellerOfferActionResponse
import com.example.myapplication.ui.feature.sell_land.model.SellerOfferListResponse
import com.example.myapplication.ui.feature.sell_land.model.SubmitResponse
import com.google.android.gms.maps.model.LatLng
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File

class SellLandRemote {

    private data class PhotoFormat(val mimeType: String, val extension: String)

    private val maxPhotoBytes = 10L * 1024L * 1024L

    private fun photoFormat(mimeType: String?): PhotoFormat {
        val normalizedMime = mimeType
            ?.substringBefore(';')
            ?.trim()
            ?.lowercase()
            ?: throw IllegalArgumentException("Cannot determine the selected photo format")

        return when (normalizedMime) {
            "image/jpeg", "image/jpg" -> PhotoFormat("image/jpeg", ".jpg")
            "image/png" -> PhotoFormat("image/png", ".png")
            "image/webp" -> PhotoFormat("image/webp", ".webp")
            else -> throw IllegalArgumentException("Unsupported photo format: $normalizedMime. Choose JPEG, PNG, or WebP.")
        }
    }

    private fun validatePhotoFile(file: File, format: PhotoFormat) {
        if (file.length() > maxPhotoBytes) {
            throw IllegalArgumentException("Photo exceeds the 10 MiB upload limit")
        }

        val header = ByteArray(12)
        val headerBytes = file.inputStream().use { it.read(header) }
        val matches = when (format.mimeType) {
            "image/jpeg" -> headerBytes >= 3 &&
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
        if (!matches) {
            throw IllegalArgumentException("Photo content does not match its reported format")
        }
    }

    fun uriToTempPhotoFile(uri: Uri, contentResolver: ContentResolver, cacheDir: File): File {
        val format = photoFormat(contentResolver.getType(uri))
        val originalName = queryName(contentResolver, uri)
        val safeBase = originalName
            ?.substringBeforeLast('.', originalName)
            ?.substringAfterLast('/')
            ?.ifBlank { "photo_${System.currentTimeMillis()}" }
            ?: "photo_${System.currentTimeMillis()}"
        val temp = File(cacheDir, "${safeBase}_${System.currentTimeMillis()}${format.extension}")

        try {
            contentResolver.openInputStream(uri).use { input ->
                temp.outputStream().use { output ->
                    input?.copyTo(output) ?: throw IllegalStateException("Cannot read selected photo")
                }
            }
            validatePhotoFile(temp, format)
            return temp
        } catch (e: Exception) {
            temp.delete()
            throw e
        }
    }

    private fun normalizeDocumentType(raw: String): String {
        return raw.trim().lowercase()
    }

    private fun normalizeMediaItem(item: SellLandMediaResponse): SellLandMediaResponse {
        return item.copy(
            mediaType = item.mediaType.trim().lowercase(),
            documentType = item.documentType?.trim()?.lowercase()
        )
    }

    suspend fun saveBoundary(requestId: Int, points: List<LatLng>): Result<Unit> = runCatching {
        val body = BoundaryRequest(points = points.map { BoundaryPoint(lat = it.latitude, lng = it.longitude) })
        val res = ApiClient.apiService.updateBoundary(requestId, body)
        if (!res.isSuccessful) throw Exception(res.errorBody()?.string() ?: "Boundary update failed")
    }

    suspend fun uploadPhoto(requestId: Int, file: File): Result<SellLandMediaResponse> = runCatching {
        val format = photoFormat(
            when (file.extension.lowercase()) {
                "jpg", "jpeg" -> "image/jpeg"
                "png" -> "image/png"
                "webp" -> "image/webp"
                else -> null
            }
        )
        validatePhotoFile(file, format)
        val req = file.asRequestBody(format.mimeType.toMediaTypeOrNull())
        val part = MultipartBody.Part.createFormData("file", file.name, req)
        val res = ApiClient.apiService.uploadPhoto(requestId, part)
        if (!res.isSuccessful || res.body() == null) {
            throw Exception(res.errorBody()?.string() ?: "Photo upload failed")
        }
        normalizeMediaItem(res.body()!!)
    }

    suspend fun uploadDocument(
        requestId: Int,
        documentType: String,
        file: File
    ): Result<SellLandMediaResponse> = runCatching {
        val normalizedType = normalizeDocumentType(documentType)
        val fileReq = file.asRequestBody("application/pdf".toMediaTypeOrNull())
        val filePart = MultipartBody.Part.createFormData("file", file.name, fileReq)
        val docTypeBody: RequestBody = normalizedType.toRequestBody("text/plain".toMediaTypeOrNull())

        val res = ApiClient.apiService.uploadDocument(requestId, docTypeBody, filePart)
        if (!res.isSuccessful || res.body() == null) {
            throw Exception(res.errorBody()?.string() ?: "Document upload failed")
        }
        normalizeMediaItem(res.body()!!)
    }

    suspend fun initiatePayment(requestId: Int, method: String): Result<PaymentResponse> = runCatching {
        val res = ApiClient.apiService.initiatePayment(PaymentInitRequest(requestId = requestId, method = method))
        if (!res.isSuccessful || res.body() == null) {
            throw Exception(res.errorBody()?.string() ?: "Payment initiation failed")
        }
        res.body()!!
    }

    suspend fun markPaid(paymentId: Int, providerRef: String? = null): Result<PaymentResponse> = runCatching {
        val res = ApiClient.apiService.markPaid(
            PaymentMarkPaidRequest(paymentId = paymentId, providerRef = providerRef)
        )
        if (!res.isSuccessful || res.body() == null) {
            throw Exception(res.errorBody()?.string() ?: "Mark paid failed")
        }
        res.body()!!
    }

    suspend fun createRazorpayOrder(requestId: Int): Result<SellLandRazorpayOrderResponse> = runCatching {
        val res = ApiClient.apiService.createSellLandRazorpayOrder(
            SellLandRazorpayOrderRequest(requestId = requestId)
        )
        if (!res.isSuccessful || res.body() == null) {
            throw Exception(res.errorBody()?.string() ?: "Order creation failed")
        }
        res.body()!!
    }

    suspend fun verifyRazorpayPayment(
        orderId: String,
        paymentId: String,
        signature: String
    ): Result<SellLandRazorpayVerifyResponse> = runCatching {
        val res = ApiClient.apiService.verifySellLandRazorpayPayment(
            SellLandRazorpayVerifyRequest(
                orderId = orderId,
                paymentId = paymentId,
                signature = signature
            )
        )
        if (!res.isSuccessful || res.body() == null) {
            throw Exception(res.errorBody()?.string() ?: "Payment verification failed")
        }
        res.body()!!
    }

    suspend fun submit(requestId: Int): Result<SubmitResponse> = runCatching {
        val res = ApiClient.apiService.submit(requestId)
        if (!res.isSuccessful || res.body() == null) {
            throw Exception(res.errorBody()?.string() ?: "Submit failed")
        }
        res.body()!!
    }

    fun uriToTempFile(uri: Uri, contentResolver: ContentResolver, cacheDir: File): File {
        val originalName = queryName(contentResolver, uri)
        val mime = contentResolver.getType(uri)
        val ext = when {
            originalName?.contains(".") == true -> originalName.substringAfterLast(".", "")
            mime == "application/pdf" -> "pdf"
            mime == "image/jpeg" -> "jpg"
            mime == "image/png" -> "png"
            else -> "pdf"
        }

        val safeBase = originalName?.substringBeforeLast(".")?.ifBlank { "upload_${System.currentTimeMillis()}" }
            ?: "upload_${System.currentTimeMillis()}"

        val temp = File(cacheDir, "${safeBase}_${System.currentTimeMillis()}.$ext")
        contentResolver.openInputStream(uri).use { input ->
            temp.outputStream().use { output ->
                input?.copyTo(output) ?: throw IllegalStateException("Cannot read file")
            }
        }
        return temp
    }

    private fun queryName(contentResolver: ContentResolver, uri: Uri): String? {
        contentResolver.query(uri, null, null, null, null)?.use { cursor ->
            val index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (index >= 0 && cursor.moveToFirst()) return cursor.getString(index)
        }
        return null
    }

    suspend fun getListingMedia(requestId: Int): Result<List<SellLandMediaResponse>> = runCatching {
        val res = ApiClient.apiService.getListingMedia(requestId)
        if (!res.isSuccessful || res.body() == null) {
            throw Exception(res.errorBody()?.string() ?: "Get media failed")
        }
        res.body()!!.map { normalizeMediaItem(it) }
    }

    suspend fun deleteListingMedia(requestId: Int, mediaId: Int): Result<Unit> = runCatching {
        val res = ApiClient.apiService.deleteListingMedia(requestId, mediaId)
        if (!res.isSuccessful) {
            throw Exception(res.errorBody()?.string() ?: "Delete media failed")
        }
    }

    suspend fun getMyListingsTracking(): Result<List<SellLandTrackingCardResponse>> = runCatching {
        val res = ApiClient.apiService.getMyListingsTracking()
        if (!res.isSuccessful || res.body() == null) {
            throw Exception(res.errorBody()?.string() ?: "Get tracking listings failed")
        }
        res.body()!!
    }

    suspend fun getMyListings(): Result<List<SellLandResponse>> = runCatching {
        val res = ApiClient.apiService.getMyListings()
        if (!res.isSuccessful || res.body() == null) {
            throw Exception(res.errorBody()?.string() ?: "Get my listings failed")
        }
        res.body()!!
    }



    suspend fun getListingDetails(requestId: Int): Result<SellLandResponse> = runCatching {
        val res = ApiClient.apiService.getListingDetails(requestId)
        if (!res.isSuccessful || res.body() == null) {
            throw Exception(res.errorBody()?.string() ?: "Get listing details failed")
        }
        res.body()!!
    }

    suspend fun cancelListing(
        requestId: Int,
        reason: String,
        upiId: String,
        notes: String? = null
    ): Result<CancelListingResponse> = runCatching {
        val res = ApiClient.apiService.cancelListing(
            id = requestId,
            body = CancelListingRequest(
                reason = reason,
                upiId = upiId,
                notes = notes
            )
        )
        if (!res.isSuccessful || res.body() == null) {
            throw Exception(res.errorBody()?.string() ?: "Cancel listing failed")
        }
        res.body()!!
    }

    suspend fun getListingOffers(requestId: Int): Result<SellerOfferListResponse> = runCatching {
        val res = ApiClient.apiService.getListingOffers(requestId)
        if (!res.isSuccessful || res.body() == null) {
            throw Exception(res.errorBody()?.string() ?: "Get offers failed")
        }
        res.body()!!
    }

    suspend fun acceptOffer(requestId: Int, offerId: Int): Result<SellerOfferActionResponse> = runCatching {
        val res = ApiClient.apiService.acceptOffer(requestId, offerId)
        if (!res.isSuccessful || res.body() == null) {
            throw Exception(res.errorBody()?.string() ?: "Accept offer failed")
        }
        res.body()!!
    }

    suspend fun rejectOffer(requestId: Int, offerId: Int): Result<SellerOfferActionResponse> = runCatching {
        val res = ApiClient.apiService.rejectOffer(requestId, offerId)
        if (!res.isSuccessful || res.body() == null) {
            throw Exception(res.errorBody()?.string() ?: "Reject offer failed")
        }
        res.body()!!
    }

    suspend fun counterOffer(
        requestId: Int,
        offerId: Int,
        counterAmount: Double
    ): Result<SellerOfferActionResponse> = runCatching {
        val res = ApiClient.apiService.counterOffer(
            id = requestId,
            offerId = offerId,
            body = CounterOfferRequest(counterAmount = counterAmount)
        )
        if (!res.isSuccessful || res.body() == null) {
            throw Exception(res.errorBody()?.string() ?: "Counter offer failed")
        }
        res.body()!!
    }

    suspend fun getDocumentRequirements(ownershipType: String? = null): Result<List<DocumentRequirementsResponse>> = runCatching {
        val res = ApiClient.apiService.getDocumentRequirements(ownershipType)
        if (!res.isSuccessful || res.body() == null) {
            throw Exception(res.errorBody()?.string() ?: "Get document requirements failed")
        }
        res.body()!!
    }
}
