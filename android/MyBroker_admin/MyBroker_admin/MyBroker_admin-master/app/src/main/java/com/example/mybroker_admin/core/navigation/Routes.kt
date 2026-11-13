package com.example.mybroker_admin.core.navigation

import android.net.Uri

object Routes {
    const val LOGIN = "login"
    const val SUPER_ADMIN_DASHBOARD = "super_admin_dashboard"
    const val SUPER_ADMIN_REVENUE = "super_admin_revenue"
    const val SOCIAL_LINKS = "social_links"
    const val BANNERS = "banners"
    const val PROCESSING_FEES = "processing_fees"
    const val SUPER_ADMIN_LISTINGS = "super_admin_listings"
    const val SUPER_ADMIN_LISTING_DETAIL = "super_admin_listing_detail/{id}"
    const val STAFF_ANALYTICS = "staff_analytics"
    const val STAFF_MANAGEMENT = "staff_management"
    const val STAFF_LIST = "staff_list"
    const val CREATE_STAFF = "create_staff"
    const val ADMIN_RATINGS = "admin_ratings"

    const val STAFF_DETAIL = "staff_detail/{staffId}"
    const val EDIT_STAFF = "edit_staff/{staffId}"

    const val ADMIN_DASHBOARD = "admin_dashboard"
    const val FIELD_DASHBOARD = "field_dashboard"

    const val LISTINGS = "listings"
    const val FINANCE = "finance"
    const val LISTING_DETAIL = "listing_detail/{id}"

    fun staffDetail(staffId: Int) = "staff_detail/$staffId"
    fun editStaff(staffId: Int) = "edit_staff/$staffId"
    fun superAdminListingDetail(id: Int) = "super_admin_listing_detail/$id"

    const val PENDING_LISTINGS = "pending_listings"
    const val ADMIN_LISTING_DETAIL = "admin_listing_detail"
    fun adminListingDetail(id: Int) = "$ADMIN_LISTING_DETAIL/$id"

    const val FIELD_AVAILABLE = "field_available"
    const val FIELD_ACTIVE_DETAIL = "field_active_detail"

    const val FIELD_SITE_VISIT = "field_site_visit/{requestId}"
    fun fieldSiteVisit(requestId: Int) = "field_site_visit/$requestId"

    const val FIELD_DOCUMENT_VIEWER =
        "field_document_viewer?docUrl={docUrl}&returnTo={returnTo}"

    fun fieldDocumentViewer(docUrl: String, returnTo: String): String {
        val encUrl = Uri.encode(docUrl)
        val encReturn = Uri.encode(returnTo)
        return "field_document_viewer?docUrl=$encUrl&returnTo=$encReturn"
    }

    const val PROFILE = "profile"
    const val CHANGE_PASSWORD = "change_password"
    const val NOTIFICATIONS = "notifications"

    const val ASSIGNED_LISTINGS = "assigned_listings"

    const val FINAL_APPROVAL = "final_approval"

    const val ADMIN_CANCEL_REFUND = "admin_cancel_refund"

    const val ACCOUNTING_DASHBOARD = "accounting_dashboard"

    const val ACCOUNTING_REFUND_LIST = "accounting_refund_list"
    const val ACCOUNTING_COMPLETED_TRANSACTIONS = "accounting_completed_transactions"
    const val ACCOUNTING_TRANSACTION_DETAIL = "accounting_transaction_detail/{listingId}"
    fun accountingTransactionDetail(listingId: String) =
        "accounting_transaction_detail/$listingId"

    const val LOCKED_LISTINGS = "locked_listings"
    const val LIVE_LISTINGS = "live_listings"
    const val BOOKED_LISTINGS = "booked_listings"
    const val BOOKED_LISTING_DETAIL = "booked_listing_detail/{listingId}"
    fun bookedListingDetail(id: Int) = "booked_listing_detail/$id"
    const val SOLD_LISTINGS = "sold_listings"
    const val SOLD_LISTING_DETAIL = "sold_listing_detail/{listingId}"
    fun soldListingDetail(id: Int) = "sold_listing_detail/$id"
    const val REGISTRY_PENDING = "registry_pending"
    const val REJECTED_LISTINGS = "rejected_listings"
    const val WEBHOOK_LOGS = "webhook_logs"

    const val REGISTRY_DASHBOARD = "registry_dashboard"
    const val REGISTRY_DETAIL = "registry_detail/{assignmentId}"
    fun registryDetail(assignmentId: String) = "registry_detail/$assignmentId"
}
