package com.example.mybroker_admin.feature.sitevisit

import java.text.ParsePosition
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

internal data class SiteVisitAuditTimelineEvent(
    val source: String,
    val recordId: String?,
    val occurredAt: String?,
    val title: String,
    val originalEvent: String?,
    val actor: String?,
    val reason: String?,
    val facts: List<String> = emptyList(),
    val sourceOrder: Int = 0
)

/** Keep the API's created-at ordering. Sorting individual pages by status breaks global page order. */
internal fun preserveSiteVisitAuditServerOrder(items: List<SiteVisitAuditItemDto>): List<SiteVisitAuditItemDto> = items.toList()

internal fun auditStatusLabel(status: String): String = when (status.trim().lowercase()) {
    "pending", "pending_payment" -> "Pending"
    "correction_required" -> "Correction Required"
    "assigned" -> "Assigned"
    "scheduled" -> "Scheduled"
    "in_progress" -> "In Progress"
    "completed" -> "Completed"
    "cancelled" -> "Cancelled"
    else -> status.replace('_', ' ').replaceFirstChar { if (it.isLowerCase()) it.titlecase(Locale.getDefault()) else it.toString() }
}

internal fun auditStatusColorKey(status: String): String = when (status.trim().lowercase()) {
    "completed", "cancelled" -> "terminal"
    "pending", "pending_payment", "correction_required", "assigned", "scheduled", "in_progress" -> "active"
    else -> "other"
}

internal fun parseSiteVisitAuditTimestamp(value: String?): Date? {
    val raw = value?.trim()?.takeIf(String::isNotEmpty) ?: return null
    val fractional = Regex("^(.*:\\d{2})\\.(\\d+)(Z|[+-]\\d{2}:\\d{2})?$").matchEntire(raw)
    val clean = fractional?.let { match ->
        val fraction = match.groupValues[2].take(3).padEnd(3, '0')
        "${match.groupValues[1]}.$fraction${match.groupValues[3]}"
    } ?: raw
    val patterns = listOf(
        "yyyy-MM-dd'T'HH:mm:ss.SSSXXX", "yyyy-MM-dd'T'HH:mm:ssXXX",
        "yyyy-MM-dd'T'HH:mm:ss.SSSX", "yyyy-MM-dd'T'HH:mm:ssX",
        "yyyy-MM-dd'T'HH:mm:ss.SSS", "yyyy-MM-dd'T'HH:mm:ss",
        "yyyy-MM-dd HH:mm:ss.SSS", "yyyy-MM-dd HH:mm:ss"
    )
    return patterns.firstNotNullOfOrNull { pattern ->
        val parser = SimpleDateFormat(pattern, Locale.ROOT).apply {
            isLenient = false
            timeZone = TimeZone.getTimeZone("UTC")
        }
        val position = ParsePosition(0)
        parser.parse(clean, position)?.takeIf { position.index == clean.length }
    }
}

internal fun formatSiteVisitAuditTimestamp(value: String?): String =
    parseSiteVisitAuditTimestamp(value)?.let {
        SimpleDateFormat("dd MMM yyyy · HH:mm", Locale.getDefault()).format(it)
    } ?: "Time unavailable"

internal fun formatSiteVisitAuditVisitDateTime(date: String?, time: String?): String {
    val formattedDate = formatSiteVisitDate(date)
    val formattedTime = formatSiteVisitTime(time)
    return if (formattedDate == "Date unavailable" || formattedTime == "Time unavailable") {
        "Visit time unavailable"
    } else "$formattedDate · $formattedTime"
}

internal fun sortSiteVisitAuditTimeline(events: List<SiteVisitAuditTimelineEvent>): List<SiteVisitAuditTimelineEvent> =
    events.withIndex().sortedWith(
        compareBy<IndexedValue<SiteVisitAuditTimelineEvent>> { parseSiteVisitAuditTimestamp(it.value.occurredAt) == null }
            .thenBy { parseSiteVisitAuditTimestamp(it.value.occurredAt)?.time ?: Long.MAX_VALUE }
            .thenBy { it.value.sourceOrder }
            .thenBy { it.index }
    ).map { it.value }

internal fun humanizeSiteVisitAuditEvent(value: String?): String {
    val clean = value?.trim().orEmpty()
    if (clean.isEmpty()) return "Audit event"
    return when (clean.uppercase()) {
        "SITE_VISIT_COMPLETED" -> "Visit completed"
        "SITE_VISIT_STARTED" -> "Visit started"
        "SITE_VISIT_ASSIGNED" -> "Field Officer assigned"
        "SITE_VISIT_REASSIGNED" -> "Field Officer reassigned"
        "SITE_VISIT_UNASSIGNED" -> "Field Officer unassigned"
        "SITE_VISIT_CORRECTION_REQUESTED" -> "Correction requested"
        "SITE_VISIT_CORRECTION_RESUBMITTED" -> "Correction response submitted"
        "SITE_VISIT_CANCELLED" -> "Booking cancelled"
        "SITE_VISIT_COMPLETION_CODE_READY" -> "Completion code ready"
        "PAYMENT_VERIFIED" -> "Payment verified"
        "BOOKING_CREATED" -> "Booking created"
        "BOOKING_PAYMENT_STATE" -> "Booking created / payment state recorded"
        "FIELD_OFFICER_COMPLETED" -> "Visit completed"
        "CORRECTION_REQUESTED" -> "Correction requested"
        "BUYER_RESUBMITTED" -> "Correction response submitted"
        "BUYER_CANCELLED", "ADMIN_CANCELLED", "IN_PROGRESS_CANCELLED" -> "Booking cancelled"
        "ASSIGN", "ASSIGNED" -> "Field Officer assigned"
        "REASSIGN", "REASSIGNED" -> "Field Officer reassigned"
        "UNASSIGN", "UNASSIGNED" -> "Field Officer unassigned"
        "CONFIRMED" -> "Refund confirmed"
        "FAILED" -> "Refund marked failed"
        else -> clean.removePrefix("SITE_VISIT_").replace('_', ' ').lowercase(Locale.getDefault())
            .replaceFirstChar { if (it.isLowerCase()) it.titlecase(Locale.getDefault()) else it.toString() }
    }
}

internal fun siteVisitAuditWorkflowTimeline(detail: SiteVisitAuditDetailDto): List<SiteVisitAuditTimelineEvent> =
    sortSiteVisitAuditTimeline(buildAuditEvents(detail, includeNotifications = false).filter { it.source != "Refund" })

internal fun siteVisitAuditRefundTimeline(detail: SiteVisitAuditDetailDto): List<SiteVisitAuditTimelineEvent> =
    sortSiteVisitAuditTimeline(buildAuditEvents(detail, includeNotifications = false).filter { it.source == "Refund" })

internal fun siteVisitAuditNotificationTimeline(detail: SiteVisitAuditDetailDto): List<SiteVisitAuditTimelineEvent> =
    sortSiteVisitAuditTimeline(buildAuditEvents(detail, includeNotifications = true).filter { it.source == "Notification" })

private fun buildAuditEvents(
    detail: SiteVisitAuditDetailDto,
    includeNotifications: Boolean
): List<SiteVisitAuditTimelineEvent> {
    val events = mutableListOf<SiteVisitAuditTimelineEvent>()
    fun addRows(source: String, rows: List<Map<String, Any?>>, sourceOrder: Int, isNotification: Boolean = false) {
        rows.forEach { row ->
            val raw = auditMapText(row, "event_type", "event", "action", "type")
            val actorMap = row["actor"] as? Map<*, *>
            val actorId = auditMapText(row, "actor_id") ?: auditMapText(actorMap, "id")
            val actorName = auditMapText(actorMap, "fullname")
            val actorRole = auditMapText(row, "actor_role", "actor_type", "recipient_role", "role_target")
            val actor = when {
                isNotification -> listOfNotNull(actorRole?.let(::auditHumanizeToken), actorId?.let { "user #$it" }).joinToString(" · ").ifBlank { null }
                actorName != null -> listOfNotNull(actorName, actorId?.let { "#$it" }).joinToString(" ")
                actorId != null -> listOfNotNull(actorRole?.let(::auditHumanizeToken), "#$actorId").joinToString(" ")
                else -> null
            }
            val facts = buildList {
                auditMapText(row, "payment_status", "status", "new_status")?.let { add("Status: ${auditHumanizeToken(it)}") }
                auditMapText(row, "order_id")?.let { add("Order: $it") }
                auditMapText(row, "payment_id")?.let { add("Payment: $it") }
                auditMapText(row, "recipient_role")?.let { add("Recipient role: ${auditHumanizeToken(it)}") }
                auditMapText(row, "user_id")?.let { add("Recipient user: #$it") }
                auditMapText(row, "is_read")?.let { add("Notification record: ${if (it == "true") "Read" else "Unread"}") }
                auditMapText(row, "actual_amount_paise")?.toLongOrNull()?.let { add("Refund amount: ₹%.2f".format(Locale.getDefault(), it / 100.0)) }
                auditMapText(row, "transaction_reference")?.let { add("Transaction reference: $it") }
                auditMapText(row, "attempt_count")?.let { add("Webhook attempts: $it") }
                auditMapText(row, "previous_field_officer")?.let { add("Previous Officer: ${auditNestedName(row["previous_field_officer"])}") }
                auditMapText(row, "field_officer")?.let { add("Assigned Officer: ${auditNestedName(row["field_officer"])}") }
            }
            events += SiteVisitAuditTimelineEvent(
                source = source,
                recordId = auditMapText(row, "id", "refund_id"),
                occurredAt = auditMapText(row, "created_at", "occurred_at", "paid_at"),
                title = humanizeSiteVisitAuditEvent(raw),
                originalEvent = raw,
                actor = actor,
                reason = auditMapText(row, "reason", "note"),
                facts = facts,
                sourceOrder = sourceOrder
            )
        }
    }
    addRows("Payment", detail.paymentHistory, 0)
    addRows("Assignment", detail.assignmentHistory, 1)
    addRows("Workflow", detail.workflowHistory, 2)
    addRows("Refund", detail.refundHistory, 3)
    if (!includeNotifications) {
        fun addBookingMilestone(timestamp: String?, rawEvent: String, title: String) {
            if (timestamp != null && events.none { it.title == title }) {
                events += SiteVisitAuditTimelineEvent(
                    source = "Booking timestamp",
                    recordId = null,
                    occurredAt = timestamp,
                    title = title,
                    originalEvent = rawEvent,
                    actor = null,
                    reason = null,
                    sourceOrder = 0
                )
            }
        }
        addBookingMilestone(detail.createdAt, "created_at", "Booking created")
        addBookingMilestone(detail.paidAt, "paid_at", "Payment verified")
        addBookingMilestone(detail.startedAt, "started_at", "Visit started")
        addBookingMilestone(detail.completedAt, "completed_at", "Visit completed")
        addBookingMilestone(detail.cancelledAt, "cancelled_at", "Booking cancelled")
    }
    if (includeNotifications) addRows("Notification", detail.notificationHistory, 4, isNotification = true)
    return events
}

private fun auditMapText(row: Map<*, *>?, vararg keys: String): String? = keys.firstNotNullOfOrNull { key ->
    row?.get(key)?.toString()?.takeIf { it.isNotBlank() && it != "null" }
}

private fun auditNestedName(value: Any?): String = (value as? Map<*, *>)?.get("fullname")?.toString()?.takeIf(String::isNotBlank) ?: "Unknown"

private fun auditHumanizeToken(value: String): String = value.replace('_', ' ').lowercase(Locale.getDefault())
    .replaceFirstChar { if (it.isLowerCase()) it.titlecase(Locale.getDefault()) else it.toString() }
