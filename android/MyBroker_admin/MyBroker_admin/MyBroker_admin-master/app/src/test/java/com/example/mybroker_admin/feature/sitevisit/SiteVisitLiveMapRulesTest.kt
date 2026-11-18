package com.example.mybroker_admin.feature.sitevisit

import com.example.mybroker_admin.data.remote.dto.BoundaryPointDto
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import com.google.maps.android.compose.MapType
import org.junit.Test

class SiteVisitLiveMapRulesTest {
    @Test
    fun mapIsVisibleOnlyDuringInProgress() {
        assertTrue(siteVisitMapVisible("in_progress"))
        listOf("assigned", "scheduled", "pending", "completed", "cancelled", "correction_required")
            .forEach { assertFalse("$it must not show live map", siteVisitMapVisible(it)) }
    }

    @Test
    fun gpsUpdatesRequireInProgressVisibleAuthorizedScreenAndPermission() {
        assertTrue(siteVisitGpsUpdatesAllowed("in_progress", true, true, true))
        assertFalse(siteVisitGpsUpdatesAllowed("completed", true, true, true))
        assertFalse(siteVisitGpsUpdatesAllowed("cancelled", true, true, true))
        assertFalse(siteVisitGpsUpdatesAllowed("in_progress", false, true, true))
        assertFalse(siteVisitGpsUpdatesAllowed("in_progress", true, false, true))
        assertFalse(siteVisitGpsUpdatesAllowed("in_progress", true, true, false))
    }

    @Test
    fun missingOrTooSmallLandBoundaryHasNoCenter() {
        assertNull(siteVisitBoundaryCenter(emptyList()))
        assertNull(siteVisitBoundaryCenter(listOf(point(1.0, 2.0), point(1.0, 2.0))))
        assertTrue(validSiteVisitBoundary(listOf(point(10.0, 20.0), point(10.5, 20.5))).isEmpty())
    }

    @Test
    fun polygonValidationRejectsInvalidCoordinatesWithoutBridgingMissingVertices() {
        val ordered = listOf(point(10.0, 20.0), point(10.5, 20.5), point(11.0, 20.0))
        assertEquals(ordered, validSiteVisitBoundary(ordered))
        assertEquals(
            emptyList<BoundaryPointDto>(),
            validSiteVisitBoundary(ordered + point(Double.NaN, 20.5))
        )
        assertTrue(validSiteVisitBoundary(listOf(point(10.0, 20.0), point(10.5, 20.5), point(91.0, 20.0))).isEmpty())
        assertTrue(validSiteVisitBoundary(listOf(point(1.0, 1.0), point(2.0, 2.0), point(3.0, 3.0))).isEmpty())
        val center = siteVisitBoundaryCenter(listOf(point(10.0, 20.0), point(10.5, 21.0), point(11.0, 20.0)))
        assertNotNull(center)
        assertEquals(10.5, center!!.lat, 0.000001)
        assertEquals(20.333333, center.lng, 0.000001)
    }

    @Test
    fun registeredBoundaryCenterIsDerivedOnlyFromValidCoordinates() {
        val center = siteVisitBoundaryCenter(listOf(point(12.0, 76.0), point(12.2, 76.0), point(12.0, 76.2)))
        assertNotNull(center)
        assertTrue(isValidSiteVisitCoordinate(center!!.lat, center.lng))
    }

    @Test
    fun mapModeToggleSwitchesBetweenNormalAndSatelliteWithoutOtherState() {
        val satellite = toggleSiteVisitMapMode(SiteVisitMapMode.NORMAL)
        assertEquals(SiteVisitMapMode.SATELLITE, satellite)
        assertEquals(MapType.SATELLITE, siteVisitMapType(satellite))
        val normal = toggleSiteVisitMapMode(satellite)
        assertEquals(SiteVisitMapMode.NORMAL, normal)
        assertEquals(MapType.NORMAL, siteVisitMapType(normal))
    }

    @Test
    fun officerToLandConnectionRequiresBothLocations() {
        assertTrue(siteVisitConnectionVisible(hasOfficerLocation = true, hasLandPolygonCenter = true))
        assertFalse(siteVisitConnectionVisible(hasOfficerLocation = false, hasLandPolygonCenter = true))
        assertFalse(siteVisitConnectionVisible(hasOfficerLocation = true, hasLandPolygonCenter = false))
        assertFalse(siteVisitConnectionVisible(hasOfficerLocation = false, hasLandPolygonCenter = false))
    }

    private fun point(lat: Double, lng: Double) = BoundaryPointDto(lat, lng)
}
