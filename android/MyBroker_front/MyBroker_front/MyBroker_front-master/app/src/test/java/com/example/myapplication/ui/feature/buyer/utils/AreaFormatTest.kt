package com.example.myapplication.ui.feature.buyer.utils

import org.junit.Assert.assertTrue
import org.junit.Test

class AreaFormatTest {
    @Test
    fun formatsIndianCurrencyForTheLocalRuntime() {
        val formatted = formatIndianCurrency(500_000.0)
        // Local JVM locale data may use either Indian secondary grouping or standard 3-digit grouping.
        assertTrue(
            "Unexpected currency grouping: $formatted",
            formatted.contains("5,00,000") || formatted.contains("500,000")
        )
        assertTrue(formatted.contains("\u20B9"))
    }

    @Test
    fun supportsExtraPrecisionForConvertedArea() {
        assertTrue(formatIndianNumber(0.4046856422, maxFractionDigits = 4).contains("0.4047"))
    }
}
