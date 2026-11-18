package com.example.mybroker_admin.feature.sitevisit

import android.Manifest
import android.content.pm.PackageManager
import android.location.Location
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.example.mybroker_admin.data.remote.dto.BoundaryPointDto
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.google.android.gms.maps.CameraUpdateFactory
import com.google.android.gms.maps.model.BitmapDescriptorFactory
import com.google.android.gms.maps.model.CameraPosition
import com.google.android.gms.maps.model.LatLngBounds
import com.google.android.gms.maps.model.LatLng
import com.google.maps.android.compose.GoogleMap
import com.google.maps.android.compose.MapProperties
import com.google.maps.android.compose.MapUiSettings
import com.google.maps.android.compose.Marker
import com.google.maps.android.compose.MarkerState
import com.google.maps.android.compose.Polygon
import com.google.maps.android.compose.Polyline
import com.google.maps.android.compose.rememberCameraPositionState
import kotlinx.coroutines.launch

@Composable
internal fun FieldOfficerSiteVisitLiveMap(
    status: String,
    bookingStillAssigned: Boolean,
    boundaryPoints: List<BoundaryPointDto>
) {
    if (!siteVisitMapVisible(status) || !bookingStillAssigned) return

    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val scope = rememberCoroutineScope()
    val fusedLocation = remember(context) { LocationServices.getFusedLocationProviderClient(context) }
    val validBoundary = remember(boundaryPoints) { validSiteVisitBoundary(boundaryPoints) }
    val landCenterPoint = remember(validBoundary) { siteVisitBoundaryCenter(validBoundary) }
    val landCenter = landCenterPoint?.let { LatLng(it.lat, it.lng) }
    var mapMode by remember { mutableStateOf(SiteVisitMapMode.NORMAL) }
    var hasFramedBothLocations by remember(validBoundary) { mutableStateOf(false) }
    var hasCenteredOnFirstOfficerFix by remember(landCenter) { mutableStateOf(landCenter != null) }
    var locationPermission by remember {
        mutableStateOf(hasForegroundLocationPermission(context))
    }
    var officerLocation by remember { mutableStateOf<LatLng?>(null) }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { result ->
        locationPermission = result[Manifest.permission.ACCESS_FINE_LOCATION] == true ||
            result[Manifest.permission.ACCESS_COARSE_LOCATION] == true ||
            hasForegroundLocationPermission(context)
    }

    DisposableEffect(status, bookingStillAssigned, locationPermission, lifecycleOwner, fusedLocation) {
        var updatesStarted = false
        val callback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                val location: Location = result.lastLocation ?: return
                if (isValidSiteVisitCoordinate(location.latitude, location.longitude)) {
                    officerLocation = LatLng(location.latitude, location.longitude)
                }
            }
        }
        val request = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, 15_000L)
            .setMinUpdateIntervalMillis(10_000L)
            .setMaxUpdateDelayMillis(30_000L)
            .build()

        fun stopUpdates() {
            if (updatesStarted) {
                fusedLocation.removeLocationUpdates(callback)
                updatesStarted = false
            }
        }

        fun startUpdates() {
            if (updatesStarted || !siteVisitGpsUpdatesAllowed(
                    status,
                    lifecycleOwner.lifecycle.currentState.isAtLeast(Lifecycle.State.STARTED),
                    locationPermission,
                    bookingStillAssigned
                ) || !hasForegroundLocationPermission(context)
            ) return
            try {
                fusedLocation.requestLocationUpdates(request, callback, context.mainLooper)
                updatesStarted = true
            } catch (_: SecurityException) {
                locationPermission = false
            }
        }

        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_START -> startUpdates()
                Lifecycle.Event.ON_RESUME -> {
                    locationPermission = hasForegroundLocationPermission(context)
                    if (locationPermission) startUpdates() else stopUpdates()
                }
                Lifecycle.Event.ON_STOP, Lifecycle.Event.ON_PAUSE -> stopUpdates()
                else -> Unit
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        startUpdates()
        onDispose {
            stopUpdates()
            lifecycleOwner.lifecycle.removeObserver(observer)
        }
    }

    val cameraState = rememberCameraPositionState()
    LaunchedEffect(landCenter) {
        landCenter?.let { cameraState.position = CameraPosition.fromLatLngZoom(it, 15f) }
    }
    LaunchedEffect(landCenter, officerLocation) {
        val officer = officerLocation
        if (landCenter != null && officer != null && !hasFramedBothLocations) {
            val bounds = LatLngBounds.Builder().apply {
                validBoundary.forEach { include(LatLng(it.lat, it.lng)) }
                include(officer)
            }.build()
            cameraState.animate(CameraUpdateFactory.newLatLngBounds(bounds, 48))
            hasFramedBothLocations = true
        } else if (landCenter == null && officer != null && !hasCenteredOnFirstOfficerFix) {
            cameraState.position = CameraPosition.fromLatLngZoom(officer, 15f)
            hasCenteredOnFirstOfficerFix = true
        }
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(9.dp)
        ) {
            Text("Site Visit Live Map", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                Text("🔴 Land Location", style = MaterialTheme.typography.labelMedium)
                Text("🔵 Officer Location", style = MaterialTheme.typography.labelMedium)
            }

            if (!locationPermission) {
                if (landCenter == null) {
                    Text("Land boundary coordinates are unavailable.", style = MaterialTheme.typography.bodySmall)
                }
                Text("Allow foreground location to show the Field Officer’s live position.", style = MaterialTheme.typography.bodySmall)
                Button(onClick = {
                    permissionLauncher.launch(arrayOf(
                        Manifest.permission.ACCESS_FINE_LOCATION,
                        Manifest.permission.ACCESS_COARSE_LOCATION
                    ))
                }) { Text("Grant location permission") }
            }

            if (validBoundary.size < 3) {
                Text(
                    "Land boundary unavailable: at least three valid ordered boundary points are required.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilterChip(
                    selected = mapMode == SiteVisitMapMode.NORMAL,
                    onClick = { mapMode = SiteVisitMapMode.NORMAL },
                    label = { Text("Map") }
                )
                FilterChip(
                    selected = mapMode == SiteVisitMapMode.SATELLITE,
                    onClick = { mapMode = SiteVisitMapMode.SATELLITE },
                    label = { Text("Satellite") }
                )
            }

            if (locationPermission && landCenter == null && officerLocation == null) {
                Text(
                    "Waiting for an officer GPS fix. No land polygon will be drawn until valid boundary points are available.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            if (landCenter != null || officerLocation != null) {
                if (landCenter == null) {
                    Text("Land boundary coordinates are unavailable; showing officer location only.", style = MaterialTheme.typography.bodySmall)
                }
                GoogleMap(
                    modifier = Modifier.fillMaxWidth().height(218.dp),
                    cameraPositionState = cameraState,
                    properties = MapProperties(mapType = siteVisitMapType(mapMode)),
                    uiSettings = MapUiSettings(zoomControlsEnabled = true, myLocationButtonEnabled = false)
                ) {
                    if (validBoundary.size >= 3) {
                        Polygon(
                            points = validBoundary.map { LatLng(it.lat, it.lng) },
                            fillColor = Color(0x553B82F6),
                            strokeColor = Color(0xFF174EA6),
                            strokeWidth = 5f
                        )
                    }
                    if (landCenter != null) {
                        Marker(
                            state = MarkerState(landCenter),
                            title = "Land Location",
                            snippet = "Center of the registered land boundary"
                        )
                    }
                    officerLocation?.let { point ->
                        Marker(
                            state = MarkerState(point),
                            title = "Officer Location",
                            icon = BitmapDescriptorFactory.defaultMarker(BitmapDescriptorFactory.HUE_AZURE)
                        )
                        val landPoint = landCenter
                        if (siteVisitConnectionVisible(officerLocation != null, landPoint != null) && landPoint != null) {
                            Polyline(
                                points = listOf(point, landPoint),
                                color = Color(0xFF7B1FA2),
                                width = 5f
                            )
                        }
                    }
                }
                if (officerLocation != null) {
                    if (landCenter != null) {
                        Text("Straight-line position reference; this is not a road route.", style = MaterialTheme.typography.bodySmall)
                    }
                    Button(onClick = {
                        scope.launch {
                            cameraState.animate(CameraUpdateFactory.newLatLngZoom(officerLocation!!, 16f))
                        }
                    }) { Text("Recenter on officer") }
                } else {
                    Text("Officer GPS fix is not available yet.", style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
}

private fun hasForegroundLocationPermission(context: android.content.Context): Boolean =
    ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
        ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
