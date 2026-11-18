package com.example.myapplication.ui.feature.sell_land

import com.example.myapplication.ui.feature.sell_land.status.OfferStatus
import com.example.myapplication.ui.feature.sell_land.status.offerStatusFromApi
import org.junit.Assert.assertEquals
import org.junit.Test

class OfferStatusMappingTest {
    @Test
    fun cancelledBookingOfferUsesSupportedExpiredState() {
        assertEquals(OfferStatus.EXPIRED, offerStatusFromApi("expired"))
        assertEquals(OfferStatus.ACCEPTED, offerStatusFromApi("accepted"))
    }
}
