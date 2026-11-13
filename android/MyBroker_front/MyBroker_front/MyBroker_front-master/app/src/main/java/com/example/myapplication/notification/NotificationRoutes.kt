package com.example.myapplication.notification

object NotificationRoutes {
    fun routeForNotification(type: String?, referenceId: String?, roleTarget: String? = null): String? {
        val id = referenceId?.toIntOrNull()
        return when (type?.uppercase()) {
            "BOOKING_PAYMENT_SUCCESS", "REGISTRY_SCHEDULED", "REGISTRY_IN_PROCESS", "REGISTRY_DONE", "REGISTRY_SOLD" ->
                id?.let { "buyer_land_details/$it" } ?: "transactions"
            "LAND_SUBMITTED", "LAND_VERIFIED", "LAND_REJECTED", "FIELD_VISIT_APPROVED", "FIELD_VISIT_REJECTED",
            "FINAL_APPROVAL_APPROVED", "FINAL_APPROVAL_REJECTED" -> id?.let { "seller_listing_detail/$it" } ?: "seller_lands"
            "CASE_ASSIGNED" -> "seller_lands"
            else -> id?.let { "land_detail/$it" }
        }
    }
}
