package com.example.myapplication.ui.feature.home_pase

import com.example.myapplication.ui.feature.buyer.data.remote.dto.IncomingOfferCountDto
import org.junit.Assert.assertEquals
import org.junit.Test

class IncomingOfferBadgeTest {
    @Test fun badgeIsHiddenForZeroAndFormatsOneToNinetyNine() {
        assertEquals(null, formatOfferBadgeCount(0))
        assertEquals("1", formatOfferBadgeCount(1))
        assertEquals("99", formatOfferBadgeCount(99))
        assertEquals("99+", formatOfferBadgeCount(100))
    }

    @Test fun badgeAggregatesBuyerAndSellerIncomingCountsOnly() {
        assertEquals(3, incomingOfferBadgeCount(IncomingOfferCountDto(3, 0, 3)))
        assertEquals(2, incomingOfferBadgeCount(IncomingOfferCountDto(0, 2, 2)))
        assertEquals(5, incomingOfferBadgeCount(IncomingOfferCountDto(3, 2, 5)))
    }
}
