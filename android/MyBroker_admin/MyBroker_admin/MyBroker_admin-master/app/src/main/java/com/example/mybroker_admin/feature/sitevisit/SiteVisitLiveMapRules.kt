package com.example.mybroker_admin.feature.sitevisit

import com.example.mybroker_admin.data.remote.dto.BoundaryPointDto

internal enum class SiteVisitMapMode { NORMAL, SATELLITE }

internal fun toggleSiteVisitMapMode(mode: SiteVisitMapMode): SiteVisitMapMode =
    if (mode == SiteVisitMapMode.NORMAL) SiteVisitMapMode.SATELLITE else SiteVisitMapMode.NORMAL

internal fun siteVisitMapType(mode: SiteVisitMapMode): com.google.maps.android.compose.MapType =
    if (mode == SiteVisitMapMode.SATELLITE) com.google.maps.android.compose.MapType.SATELLITE
    else com.google.maps.android.compose.MapType.NORMAL

internal fun siteVisitMapVisible(status: String?): Boolean =
    status.equals("in_progress", ignoreCase = true)

internal fun siteVisitGpsUpdatesAllowed(
    status: String?,
    screenStarted: Boolean,
    hasLocationPermission: Boolean,
    bookingStillAssigned: Boolean
): Boolean = siteVisitMapVisible(status) && screenStarted && hasLocationPermission && bookingStillAssigned

internal fun isValidSiteVisitCoordinate(lat: Double, lng: Double): Boolean =
    lat.isFinite() && lng.isFinite() && lat in -90.0..90.0 && lng in -180.0..180.0

internal fun validSiteVisitBoundary(points: List<BoundaryPointDto>): List<BoundaryPointDto> =
    points.takeIf { boundary ->
        boundary.size >= 3 &&
            boundary.all { isValidSiteVisitCoordinate(it.lat, it.lng) } &&
            boundary.map { it.lat to it.lng }.distinct().size >= 3 &&
            boundaryTwiceArea(boundary) != 0.0
    }.orEmpty()

/** The listing stores boundary vertices rather than a separate land pin. */
internal fun siteVisitBoundaryCenter(points: List<BoundaryPointDto>): BoundaryPointDto? {
    val valid = validSiteVisitBoundary(points)
    if (valid.size < 3) return null
    val vertices = if (valid.first() == valid.last()) valid.dropLast(1) else valid
    if (vertices.size < 3) return null
    val twiceArea = boundaryTwiceArea(vertices)
    var longitudeWeightedSum = 0.0
    var latitudeWeightedSum = 0.0
    vertices.indices.forEach { index ->
        val current = vertices[index]
        val next = vertices[(index + 1) % vertices.size]
        val cross = current.lng * next.lat - next.lng * current.lat
        longitudeWeightedSum += (current.lng + next.lng) * cross
        latitudeWeightedSum += (current.lat + next.lat) * cross
    }
    if (twiceArea == 0.0) return null
    val center = BoundaryPointDto(
        lat = latitudeWeightedSum / (3.0 * twiceArea),
        lng = longitudeWeightedSum / (3.0 * twiceArea)
    )
    return center.takeIf { isValidSiteVisitCoordinate(it.lat, it.lng) }
}

internal fun siteVisitConnectionVisible(hasOfficerLocation: Boolean, hasLandPolygonCenter: Boolean): Boolean =
    hasOfficerLocation && hasLandPolygonCenter

private fun boundaryTwiceArea(points: List<BoundaryPointDto>): Double {
    val vertices = if (points.size > 1 && points.first() == points.last()) points.dropLast(1) else points
    if (vertices.size < 3) return 0.0
    return vertices.indices.sumOf { index ->
        val current = vertices[index]
        val next = vertices[(index + 1) % vertices.size]
        current.lng * next.lat - next.lng * current.lat
    }
}
