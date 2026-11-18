package com.example.myapplication.ui.feature.buyer.utils

import java.text.NumberFormat
import java.util.Locale

fun formatIndianNumber(value: Double, maxFractionDigits: Int = 2): String {
    return NumberFormat.getNumberInstance(Locale("en", "IN")).apply {
        maximumFractionDigits = maxFractionDigits.coerceAtLeast(0)
        minimumFractionDigits = 0
    }.format(value)
}

fun formatAreaWithUnit(area: Double, areaUnit: String): String {
    val formattedArea = formatIndianNumber(area)

    val displayUnit = when (areaUnit.trim().lowercase()) {
        "sqft" -> "sq ft"
        "sqm" -> "sq m"
        "acre" -> "acre"
        "bigha" -> "bigha"
        else -> areaUnit.trim()
    }

    return listOf(formattedArea, displayUnit).filter { it.isNotBlank() }.joinToString(" ")
}

fun formatIndianCurrency(value: Double): String {
    return NumberFormat.getCurrencyInstance(Locale("en", "IN")).apply {
        maximumFractionDigits = 2
        minimumFractionDigits = 0
    }.format(value)
}
