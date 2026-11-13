// SiteVisitViewModel.kt
package com.example.mybroker_admin.feature.fieldofficer.sitevisit

import android.Manifest
import android.annotation.SuppressLint
import android.app.Application
import android.content.pm.PackageManager
import androidx.core.content.ContextCompat
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.remote.dto.FieldOfficerCaseDetailResponse
import com.example.mybroker_admin.data.repository.FieldOfficerRepository
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.google.android.gms.maps.model.LatLng
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MultipartBody
import retrofit2.HttpException
import org.json.JSONObject
import java.net.URL
import javax.net.ssl.HttpsURLConnection

data class SiteVisitUiState(
    val loading: Boolean = false,
    val submitting: Boolean = false,
    val error: String? = null,
    val successMessage: String? = null,
    val photoUploadMessage: String? = null,
    val detail: FieldOfficerCaseDetailResponse? = null,
    val visitPhotoUrl: String? = null,
    val currentLocation: LatLng? = null,
    val routePoints: List<LatLng> = emptyList()
)

class SiteVisitViewModel(application: Application) : AndroidViewModel(application) {
    private val repository = FieldOfficerRepository(ApiClient.fieldOfficerApi)
    private val fusedClient = LocationServices.getFusedLocationProviderClient(application)

    private val _uiState = MutableStateFlow(SiteVisitUiState())
    val uiState: StateFlow<SiteVisitUiState> = _uiState

    private var destination: LatLng? = null

    private val locationCallback = object : LocationCallback() {
        override fun onLocationResult(result: LocationResult) {
            val loc = result.lastLocation ?: return
            val current = LatLng(loc.latitude, loc.longitude)

            _uiState.value = _uiState.value.copy(currentLocation = current)

            val dest = destination ?: return
            viewModelScope.launch {
                val route = fetchRoadRoute(current, dest)
                _uiState.value = _uiState.value.copy(
                    routePoints = if (route.isNotEmpty()) route else listOf(current, dest)
                )
            }
        }
    }

    fun loadCaseDetail(requestId: Int) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                loading = true,
                error = null,
                successMessage = null,
                photoUploadMessage = null
            )
            try {
                val detail = repository.getCaseDetail(requestId)
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    detail = detail,
                    visitPhotoUrl = detail.field_officer_visit_photo_url
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    error = extractErrorMessage(e, "Failed to load case")
                )
            }
        }
    }

    fun startTracking(destination: LatLng) {
        this.destination = destination
        startLocationUpdates()
    }

    fun stopTracking() {
        fusedClient.removeLocationUpdates(locationCallback)
    }

    @SuppressLint("MissingPermission")
    private fun startLocationUpdates() {
        val context = getApplication<Application>()
        val granted = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        if (!granted) return

        val request = LocationRequest.Builder(
            Priority.PRIORITY_HIGH_ACCURACY,
            5000L
        ).setMinUpdateIntervalMillis(3000L).build()

        fusedClient.requestLocationUpdates(request, locationCallback, context.mainLooper)
    }

    private fun getMapsApiKeyFromManifest(): String {
        return try {
            val app = getApplication<Application>()
            val appInfo = app.packageManager.getApplicationInfo(
                app.packageName,
                PackageManager.GET_META_DATA
            )
            appInfo.metaData?.getString("com.google.android.geo.API_KEY").orEmpty()
        } catch (_: Exception) {
            ""
        }
    }

    private suspend fun fetchRoadRoute(origin: LatLng, destination: LatLng): List<LatLng> {
        return withContext(Dispatchers.IO) {
            try {
                val apiKey = getMapsApiKeyFromManifest()
                if (apiKey.isBlank()) return@withContext emptyList()

                val url =
                    "https://maps.googleapis.com/maps/api/directions/json?" +
                            "origin=${origin.latitude},${origin.longitude}" +
                            "&destination=${destination.latitude},${destination.longitude}" +
                            "&mode=driving&key=$apiKey"

                val connection = (URL(url).openConnection() as HttpsURLConnection).apply {
                    requestMethod = "GET"
                    connectTimeout = 10000
                    readTimeout = 10000
                }

                connection.inputStream.bufferedReader().use { reader ->
                    val body = reader.readText()
                    val json = JSONObject(body)
                    val routes = json.optJSONArray("routes") ?: return@use emptyList<LatLng>()
                    if (routes.length() == 0) return@use emptyList<LatLng>()

                    val poly = routes.getJSONObject(0)
                        .getJSONObject("overview_polyline")
                        .getString("points")

                    decodePolyline(poly)
                }
            } catch (_: Exception) {
                emptyList()
            }
        }
    }

    private fun decodePolyline(encoded: String): List<LatLng> {
        val poly = ArrayList<LatLng>()
        var index = 0
        var lat = 0
        var lng = 0

        while (index < encoded.length) {
            var b: Int
            var shift = 0
            var result = 0
            do {
                b = encoded[index++].code - 63
                result = result or ((b and 0x1f) shl shift)
                shift += 5
            } while (b >= 0x20)
            val dlat = if ((result and 1) != 0) (result shr 1).inv() else result shr 1
            lat += dlat

            shift = 0
            result = 0
            do {
                b = encoded[index++].code - 63
                result = result or ((b and 0x1f) shl shift)
                shift += 5
            } while (b >= 0x20)
            val dlng = if ((result and 1) != 0) (result shr 1).inv() else result shr 1
            lng += dlng

            poly.add(LatLng(lat / 1E5, lng / 1E5))
        }

        return poly
    }

    fun uploadVisitPhoto(requestId: Int, filePart: MultipartBody.Part) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                submitting = true,
                error = null,
                successMessage = null,
                photoUploadMessage = null
            )
            try {
                val res = repository.uploadVisitPhoto(requestId, filePart)
                _uiState.value = _uiState.value.copy(
                    submitting = false,
                    visitPhotoUrl = res.visit_photo_url,
                    photoUploadMessage = "Photo uploaded"
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    submitting = false,
                    error = extractErrorMessage(e, "Photo upload failed")
                )
            }
        }
    }

    fun approve(requestId: Int, notes: String) {
        if (_uiState.value.visitPhotoUrl.isNullOrBlank()) {
            _uiState.value = _uiState.value.copy(
                error = "Visit photo is required before approval"
            )
            return
        }

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                submitting = true,
                error = null,
                successMessage = null,
                photoUploadMessage = null
            )
            try {
                repository.submitReview(
                    requestId = requestId,
                    decision = "approved",
                    notes = notes.ifBlank { null },
                    rejectReason = null
                )
                _uiState.value = _uiState.value.copy(
                    submitting = false,
                    successMessage = "Approved successfully"
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    submitting = false,
                    error = extractErrorMessage(e, "Approve failed")
                )
            }
        }
    }


    fun reject(requestId: Int, notes: String, reason: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                submitting = true,
                error = null,
                successMessage = null,
                photoUploadMessage = null
            )
            try {
                repository.submitReview(
                    requestId = requestId,
                    decision = "rejected",
                    notes = notes.ifBlank { null },
                    rejectReason = reason
                )
                _uiState.value = _uiState.value.copy(
                    submitting = false,
                    successMessage = "Rejected successfully"
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    submitting = false,
                    error = extractErrorMessage(e, "Reject failed")
                )
            }
        }
    }

    fun clearSuccess() {
        _uiState.value = _uiState.value.copy(successMessage = null)
    }

    override fun onCleared() {
        super.onCleared()
        stopTracking()
    }

    private fun extractErrorMessage(e: Exception, fallback: String): String {
        if (e is HttpException) {
            val body = try { e.response()?.errorBody()?.string() } catch (_: Exception) { null }
            if (!body.isNullOrBlank()) {
                val detail = runCatching { JSONObject(body).optString("detail") }.getOrNull()
                if (!detail.isNullOrBlank()) return detail
            }
            return "HTTP ${e.code()}: ${e.message()}"
        }
        return e.message ?: fallback
    }
}
