package com.example.myapplication.ui.feature.buyer.land_detail.components

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.myapplication.ui.feature.buyer.land_detail.LandDetail
import com.example.myapplication.ui.feature.buyer.utils.LandAreaPriceCalculator
import com.example.myapplication.ui.feature.buyer.utils.LandAreaPriceRow
import com.example.myapplication.ui.feature.buyer.utils.formatIndianNumber
import com.example.myapplication.ui.feature.buyer.utils.formatAreaWithUnit
import java.text.NumberFormat
import java.util.Locale

@Composable
fun LandInfoSection(land: LandDetail) {
    val breakdown = LandAreaPriceCalculator.calculate(
        area = land.area,
        areaUnit = land.areaUnit,
        expectedPrice = land.expectedPrice,
        priceType = land.priceType
    )

    Column(
        modifier = Modifier.padding(16.dp)
    ) {
        Text(
            text = "Total Land Amount: ${breakdown.totalLandAmount?.let(::formatCurrency) ?: "Unavailable"}",
            style = MaterialTheme.typography.headlineMedium
        )

        Spacer(modifier = Modifier.height(6.dp))

        Text("Title: ${land.title}")
        Text("Land Type: ${land.landType.replace('_', ' ').replaceFirstChar { it.uppercase() }}")
        Text("Category: ${categoryText(land.ownerCategory)}")
        Text("Status: ${statusText(land.statusLabel)}")
        Text("Area: ${formatAreaWithUnit(land.area, land.areaUnit)}")

        Spacer(modifier = Modifier.height(12.dp))
        Text("Area and Per Unit Price", style = MaterialTheme.typography.titleMedium)
        Spacer(modifier = Modifier.height(6.dp))
        AreaPriceTable(rows = breakdown.rows)

        val district = land.city ?: "-"
        val state = land.state ?: "-"
        val pincode = land.pincode ?: "-"
        Text("District: $district")
        Text("State: $state")
        Text("Pincode: $pincode")

        Spacer(modifier = Modifier.height(8.dp))
    }
}

@Composable
private fun AreaPriceTable(rows: List<LandAreaPriceRow>) {
    Column(modifier = Modifier.fillMaxWidth()) {
        HorizontalDivider()
        AreaPriceTableRow(
            first = "Unit",
            second = "Converted Area",
            third = "Per Unit Price",
            header = true
        )
        HorizontalDivider()
        rows.forEachIndexed { index, row ->
            AreaPriceTableRow(
                first = row.unitLabel,
                second = row.convertedArea?.let(::formatIndianNumber) ?: "—",
                third = row.perUnitPrice?.let(::formatCurrency) ?: "—"
            )
            if (index < rows.lastIndex) HorizontalDivider()
        }
        HorizontalDivider()
    }
}

@Composable
private fun AreaPriceTableRow(
    first: String,
    second: String,
    third: String,
    header: Boolean = false
) {
    val style = if (header) MaterialTheme.typography.labelMedium else MaterialTheme.typography.bodySmall
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        verticalAlignment = androidx.compose.ui.Alignment.CenterVertically
    ) {
        Text(first, modifier = Modifier.weight(0.8f), style = style)
        Text(second, modifier = Modifier.weight(1.1f), style = style)
        Text(third, modifier = Modifier.weight(1.25f), style = style)
    }
}

private fun statusText(raw: String): String {
    val normalized = raw.trim().lowercase(Locale.ROOT)
    return when {
        normalized == "available" -> "Available"
        normalized == "temp_lock" || normalized == "locked" || normalized == "lock" -> "Lock"
        normalized == "booked" -> "Booked"
        normalized == "sold" -> "Sold"
        else -> raw.replace('_', ' ').replaceFirstChar { it.uppercase() }
    }
}

private fun categoryText(raw: String?): String {
    return when (raw?.trim()?.lowercase()) {
        "general" -> "General"
        "obc" -> "OBC"
        "sc" -> "SC"
        "st" -> "ST"
        null, "" -> "-"
        else -> raw.replace('_', ' ').replaceFirstChar { it.uppercase() }
    }
}

private fun formatCurrency(value: Double): String {
    return NumberFormat.getCurrencyInstance(Locale("en", "IN")).apply {
        maximumFractionDigits = 2
        minimumFractionDigits = 0
    }.format(value)
}
