package com.example.myapplication.ui.feature.sell_land.model



data class PricingDetails(
    val priceType: String,
    val price: Double,
    val negotiable: Boolean,
    val availability: String,
    val pricingVersion: Int = 2
) {
    val isLegacyPerUnit: Boolean
        get() = pricingVersion == 1 && priceType.trim().lowercase() in setOf(
            "price_per_unit",
            "price per unit",
            "price per sq.ft",
            "price per sqft"
        )
}

data class SellerPricingRequestFields(
    val pricingVersion: Int?,
    val priceType: String?,
    val expectedPrice: Double?
)

fun sellerPricingRequestFields(pricing: PricingDetails?): SellerPricingRequestFields {
    if (pricing?.isLegacyPerUnit == true) {
        // Omit all pricing fields so an unrelated draft save preserves the stored V1 rate.
        return SellerPricingRequestFields(null, null, null)
    }
    if (pricing == null) {
        return SellerPricingRequestFields(2, "total_price", null)
    }
    if (pricing.pricingVersion == 1) {
        return SellerPricingRequestFields(1, "total_price", pricing.price)
    }
    return SellerPricingRequestFields(2, "total_price", pricing.price)
}
