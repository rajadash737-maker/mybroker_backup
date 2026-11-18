package com.example.myapplication.notification

object NotificationRoutes {
    fun routeForNotification(type: String?, referenceId: String?, roleTarget: String? = null): String? {
        val id = referenceId?.toIntOrNull()
        if (type?.startsWith("SITE_VISIT_", ignoreCase = true) == true) return id?.let { "my_site_visits/$it" } ?: "my_site_visits"
        return when (type?.uppercase()) {
            "SITE_VISIT_COMPLETED", "SITE_VISIT_COMPLETION_CODE_READY", "SITE_VISIT_ASSIGNED" -> "my_site_visits"
            "BOOKING_PAYMENT_SUCCESS", "REGISTRY_SCHEDULED", "REGISTRY_IN_PROCESS", "REGISTRY_DONE", "REGISTRY_SOLD" ->
                id?.let { "buyer_land_details/$it" } ?: "transactions"
            "LAND_SUBMITTED", "LAND_VERIFIED", "LAND_REJECTED", "FIELD_VISIT_APPROVED", "FIELD_VISIT_REJECTED",
            "FINAL_APPROVAL_APPROVED", "FINAL_APPROVAL_REJECTED" -> id?.let { "seller_listing_detail/$it" } ?: "seller_lands"
            "CASE_ASSIGNED" -> "seller_lands"
            else -> id?.let { "land_detail/$it" }
        }
    }
}

