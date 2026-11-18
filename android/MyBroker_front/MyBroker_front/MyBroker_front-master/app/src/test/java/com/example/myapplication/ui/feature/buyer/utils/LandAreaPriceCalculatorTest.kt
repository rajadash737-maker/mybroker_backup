package com.example.myapplication.ui.feature.buyer.utils

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class LandAreaPriceCalculatorTest {
    @Test
    fun convertsAreaFromAcreIntoAllSupportedUnits() {
        val result = LandAreaPriceCalculator.calculate(1.0, "acre", 435_600.0, "total_price")

        assertEquals(43_560.0, result.rows[0].convertedArea!!, 0.001)
        assertEquals(4_046.856422, result.rows[1].convertedArea!!, 0.001)
        assertEquals(100.0, result.rows[2].convertedArea!!, 0.001)
        assertEquals(1.0, result.rows[3].convertedArea!!, 0.001)
        assertEquals(0.4046856422, result.rows[4].convertedArea!!, 0.000001)
    }

    @Test
    fun totalPriceIsDividedByEachConvertedArea() {
        val result = LandAreaPriceCalculator.calculate(1.0, "acre", 435_600.0, "total_price")

        assertEquals(435_600.0, result.totalLandAmount!!, 0.001)
        assertEquals(10.0, result.rows[0].perUnitPrice!!, 0.001)
        assertEquals(4_356.0, result.rows[2].perUnitPrice!!, 0.001)
        assertEquals(435_600.0, result.rows[3].perUnitPrice!!, 0.001)
    }

    @Test
    fun pricePerUnitUsesSquareFeetAsTheInputPriceUnit() {
        val result = LandAreaPriceCalculator.calculate(2.0, "acre", 10.0, "price_per_unit")

        assertEquals(871_200.0, result.totalLandAmount!!, 0.001)
        assertEquals(10.0, result.rows[0].perUnitPrice!!, 0.001)
        assertEquals(4_35_600.0, result.rows[3].perUnitPrice!!, 0.001)
    }

    @Test
    fun legacyBighaKeepsKnownTotalButDoesNotGuessConversions() {
        val result = LandAreaPriceCalculator.calculate(2.0, "bigha", 500_000.0, "total_price")

        assertEquals(500_000.0, result.totalLandAmount!!, 0.001)
        result.rows.forEach {
            assertNull(it.convertedArea)
            assertNull(it.perUnitPrice)
        }

        val perSquareFootPrice = LandAreaPriceCalculator.calculate(2.0, "bigha", 10.0, "price_per_unit")
        assertNull(perSquareFootPrice.totalLandAmount)
        perSquareFootPrice.rows.forEach {
            assertNull(it.convertedArea)
            assertNull(it.perUnitPrice)
        }
    }

    @Test
    fun invalidAreaOrPriceDoesNotProduceMisleadingCalculations() {
        val invalidArea = LandAreaPriceCalculator.calculate(0.0, "sqft", 100.0, "total_price")
        assertEquals(100.0, invalidArea.totalLandAmount!!, 0.001)
        assertNull(invalidArea.rows.first().convertedArea)
        assertNull(invalidArea.rows.first().perUnitPrice)

        val invalidPrice = LandAreaPriceCalculator.calculate(100.0, "sqft", -10.0, "total_price")
        assertEquals(100.0, invalidPrice.rows.first().convertedArea!!, 0.001)
        assertNull(invalidPrice.totalLandAmount)
        assertNull(invalidPrice.rows.first().perUnitPrice)
    }

    @Test
    fun agreedDealAmountIsDividedByConvertedAreaInEveryUnit() {
        val result = LandAreaPriceCalculator.calculateForAgreedDeal(1.0, "acre", 500_000.0)

        assertEquals(500_000.0, result.totalLandAmount!!, 0.001)
        assertEquals(43_560.0, result.rows[0].convertedArea!!, 0.001)
        assertEquals(500_000.0 / 43_560.0, result.rows[0].perUnitPrice!!, 0.000001)
        assertEquals(500_000.0, result.rows[3].perUnitPrice!!, 0.001)
    }

    @Test
    fun agreedDealSupportsDecimalAndHectareSourceUnits() {
        val decimal = LandAreaPriceCalculator.calculateForAgreedDeal(100.0, "decimal", 500_000.0)
        assertEquals(100.0, decimal.rows[2].convertedArea!!, 0.001)
        assertEquals(5_000.0, decimal.rows[2].perUnitPrice!!, 0.001)

        val hectare = LandAreaPriceCalculator.calculateForAgreedDeal(1.0, "hectare", 500_000.0)
        assertEquals(1.0, hectare.rows[4].convertedArea!!, 0.000001)
        assertEquals(500_000.0, hectare.rows[4].perUnitPrice!!, 0.001)
    }

    @Test
    fun agreedDealDoesNotCalculateForMissingInvalidAreaOrLegacyBigha() {
        val missingDeal = LandAreaPriceCalculator.calculateForAgreedDeal(1.0, "acre", null)
        assertNull(missingDeal.totalLandAmount)
        assertNull(missingDeal.rows.first().perUnitPrice)

        val invalidDeal = LandAreaPriceCalculator.calculateForAgreedDeal(1.0, "acre", -10.0)
        assertNull(invalidDeal.totalLandAmount)
        assertNull(invalidDeal.rows.first().perUnitPrice)

        val zeroArea = LandAreaPriceCalculator.calculateForAgreedDeal(0.0, "sqft", 500_000.0)
        assertEquals(500_000.0, zeroArea.totalLandAmount!!, 0.001)
        assertNull(zeroArea.rows.first().convertedArea)
        assertNull(zeroArea.rows.first().perUnitPrice)

        val bigha = LandAreaPriceCalculator.calculateForAgreedDeal(2.0, "bigha", 500_000.0)
        assertEquals(500_000.0, bigha.totalLandAmount!!, 0.001)
        bigha.rows.forEach {
            assertNull(it.convertedArea)
            assertNull(it.perUnitPrice)
        }
    }
}
