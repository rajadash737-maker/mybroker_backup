package com.example.mybroker_admin.notification

import com.example.mybroker_admin.core.navigation.Routes

object NotificationRoutes {
    fun routeForProperty(propertyId: String?, role: String?): String? {
        val id = propertyId?.toIntOrNull() ?: return null
        return when (role) {
            "super_admin" -> Routes.superAdminListingDetail(id)
            "admin" -> Routes.adminListingDetail(id)
            "accounting" -> Routes.adminListingDetail(id)
            else -> Routes.adminListingDetail(id)
        }
    }

    fun routeForNotification(type: String?, referenceId: String?, role: String?): String? {
        if (type?.startsWith("SITE_VISIT_") == true && referenceId?.toIntOrNull() != null) {
            val id = referenceId.toInt()
            return when (role?.lowercase()) {
                "field_officer" -> if (type == NotificationData.TYPE_SITE_VISIT_ASSIGNMENT_REMOVED) {
                    Routes.FIELD_SITE_VISITS
                } else {
                    Routes.fieldSiteVisitBookingDetail(id)
                }
                "accounting" -> Routes.accountingSiteVisitRefundDetail(id)
                "super_admin" -> Routes.superAdminSiteVisitAuditDetail(id)
                "admin" -> Routes.siteVisitAdminDetail(id)
                else -> null
            }
        }
        return when (type) {
            NotificationData.TYPE_SITE_VISIT_ASSIGNED -> Routes.FIELD_SITE_VISITS
            NotificationData.TYPE_SITE_VISIT_ASSIGNMENT_REMOVED -> Routes.FIELD_SITE_VISITS
            NotificationData.TYPE_SITE_VISIT_COMPLETED, NotificationData.TYPE_SITE_VISIT_COMPLETION_CODE_READY ->
                if (role.equals("field_officer", ignoreCase = true)) Routes.FIELD_SITE_VISITS else Routes.SITE_VISITS
            NotificationData.TYPE_LAND_SUBMITTED -> Routes.PENDING_LISTINGS
            NotificationData.TYPE_CASE_ASSIGNED -> Routes.FIELD_AVAILABLE
            NotificationData.TYPE_REGISTRY_SCHEDULED -> referenceId?.let { Routes.registryDetail(it) } ?: Routes.REGISTRY_DASHBOARD
            NotificationData.TYPE_REGISTRY_IN_PROCESS,
            NotificationData.TYPE_REGISTRY_DONE,
            NotificationData.TYPE_REGISTRY_SOLD -> referenceId?.toIntOrNull()?.let { Routes.bookedListingDetail(it) } ?: Routes.BOOKED_LISTINGS
            NotificationData.TYPE_FIELD_VISIT_APPROVED -> routeForProperty(referenceId, role)
            NotificationData.TYPE_FIELD_VISIT_REJECTED -> routeForProperty(referenceId, role)
            NotificationData.TYPE_FINAL_APPROVAL_APPROVED -> routeForProperty(referenceId, role)
            NotificationData.TYPE_FINAL_APPROVAL_REJECTED -> routeForProperty(referenceId, role)
            NotificationData.TYPE_LISTING_LOCKED_FOR_ADMIN -> Routes.LOCKED_LISTINGS
            NotificationData.TYPE_BOOKING_PAYMENT_SUCCESS -> referenceId?.toIntOrNull()?.let { Routes.bookedListingDetail(it) } ?: Routes.BOOKED_LISTINGS
            NotificationData.TYPE_LAND_VERIFIED,
            NotificationData.TYPE_LAND_REJECTED -> routeForProperty(referenceId, role)
            else -> routeForProperty(referenceId, role)
        }
    }
}

