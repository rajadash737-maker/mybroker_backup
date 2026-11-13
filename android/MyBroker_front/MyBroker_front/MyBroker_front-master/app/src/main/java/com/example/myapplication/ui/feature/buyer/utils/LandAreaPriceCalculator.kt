package com.example.myapplication.ui.feature.buyer.utils

data class LandAreaPriceRow(
    val unitLabel: String,
    val convertedArea: Double?,
    val perUnitPrice: Double?
)

data class LandAreaPriceBreakdown(
    val totalLandAmount: Double?,
    val rows: List<LandAreaPriceRow>
)

object LandAreaPriceCalculator {
    private data class Unit(val key: String, val label: String, val squareFeet: Double)

    private val units = listOf(
        Unit("sqft", "Sq.ft", 1.0),
        Unit("sqm", "Sq.m", 10.7639104167),
        Unit("decimal", "Decimal", 435.6),
        Unit("acre", "Acre", 43_560.0),
        Unit("hectare", "Hectare", 107_639.104167)
    )

    fun calculate(
        area: Double?,
        areaUnit: String?,
        expectedPrice: Double?,
        priceType: String?
    ): LandAreaPriceBreakdown {
        val inputArea = area?.takeIf { it.isFinite() && it > 0.0 }
        val inputPrice = expectedPrice?.takeIf { it.isFinite() && it > 0.0 }
        val sourceUnit = units.firstOrNull { it.key == areaUnit?.trim()?.lowercase() }
        val totalSquareFeet = if (inputArea != null && sourceUnit != null) {
            (inputArea * sourceUnit.squareFeet).takeIf { it.isFinite() && it > 0.0 }
        } else {
            null
        }

        val normalizedPriceType = priceType?.trim()?.lowercase()
        val totalAmount = when {
            inputPrice == null -> null
            normalizedPriceType == "total_price" -> inputPrice
            normalizedPriceType == "price_per_unit" && totalSquareFeet != null ->
                (inputPrice * totalSquareFeet).takeIf { it.isFinite() && it > 0.0 }
            else -> null
        }

        val pricePerSquareFoot = when {
            inputPrice == null -> null
            normalizedPriceType == "total_price" && totalSquareFeet != null -> inputPrice / totalSquareFeet
            normalizedPriceType == "price_per_unit" && totalSquareFeet != null -> inputPrice
            else -> null
        }?.takeIf { it.isFinite() && it > 0.0 }

        val rows = units.map { unit ->
            val convertedArea = totalSquareFeet
                ?.div(unit.squareFeet)
                ?.takeIf { it.isFinite() && it > 0.0 }
            val perUnitPrice = pricePerSquareFoot
                ?.times(unit.squareFeet)
                ?.takeIf { it.isFinite() && it > 0.0 }
            LandAreaPriceRow(unit.label, convertedArea, perUnitPrice)
        }

        return LandAreaPriceBreakdown(totalAmount, rows)
    }
}
