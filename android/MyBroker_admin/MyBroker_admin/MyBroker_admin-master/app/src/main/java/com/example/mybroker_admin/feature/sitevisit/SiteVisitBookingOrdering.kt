package com.example.mybroker_admin.feature.sitevisit

import java.text.ParsePosition
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

/** Sorts a copy of the queue by active/terminal group, then local visit time, then booking ID. */
internal fun sortSiteVisitBookings(bookings: List<SiteVisitListItemDto>): List<SiteVisitListItemDto> =
    sortByVisitTime(bookings, { it.status }, { it.visitDate }, { it.visitTime }, { it.id })

internal fun sortFieldOfficerSiteVisits(bookings: List<FieldOfficerVisitDto>): List<FieldOfficerVisitDto> =
    sortByVisitTime(bookings, { it.status }, { it.visitDate }, { it.visitTime }, { it.id })

internal fun filterFieldOfficerSiteVisits(
    bookings: List<FieldOfficerVisitDto>,
    status: String
): List<FieldOfficerVisitDto> = bookings.filter {
    status.equals("all", ignoreCase = true) || it.status.equals(status, ignoreCase = true)
}

private data class DatedVisit<T>(val booking: T, val terminal: Boolean, val visitTime: Date?, val id: Int)

private fun <T> sortByVisitTime(
    bookings: List<T>,
    status: (T) -> String,
    date: (T) -> String,
    time: (T) -> String,
    id: (T) -> Int
): List<T> = bookings.map { booking ->
    DatedVisit(booking, status(booking).isTerminalSiteVisitStatus(), parseSiteVisitDateTime(date(booking), time(booking)), id(booking))
}.sortedWith(
    compareBy<DatedVisit<T>> { it.terminal }
        .thenBy { it.visitTime == null }
        .thenBy { it.visitTime?.time ?: Long.MAX_VALUE }
        .thenBy { it.id }
).map { it.booking }

internal fun formatSiteVisitDateTime(date: String?, time: String?): String =
    parseSiteVisitDateTime(date, time)?.let { parsed ->
        SimpleDateFormat("d MMM yyyy · HH:mm", Locale.getDefault()).format(parsed)
    } ?: "Visit time unavailable"

internal fun formatSiteVisitDate(value: String?): String =
    parseSiteVisitDate(value)?.let { parsed ->
        SimpleDateFormat("dd MMM yyyy", Locale.getDefault()).format(parsed)
    } ?: "Date unavailable"

internal fun formatSiteVisitTime(value: String?): String =
    parseSiteVisitTime(value)?.let { parsed ->
        SimpleDateFormat("HH:mm", Locale.getDefault()).apply {
            timeZone = TimeZone.getTimeZone("UTC")
        }.format(parsed)
    } ?: "Time unavailable"

private fun String.isTerminalSiteVisitStatus(): Boolean =
    equals("completed", ignoreCase = true) || equals("cancelled", ignoreCase = true)

/** Backend date/time fields are local wall-clock values; interpret both in the device's local zone. */
internal fun parseSiteVisitDateTime(date: String?, time: String?): Date? {
    if (date == null || time == null) return null
    val cleanDate = date.trim()
    val cleanTime = time.trim()
    if (!DATE_PATTERN.matches(cleanDate) || !TIME_PATTERN.matches(cleanTime)) return null
    val normalizedTime = if (cleanTime.length == 5) "$cleanTime:00" else cleanTime
    val parser = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.ROOT).apply {
        isLenient = false
        timeZone = TimeZone.getDefault()
    }
    val input = "$cleanDate $normalizedTime"
    val position = ParsePosition(0)
    return parser.parse(input, position)?.takeIf { position.index == input.length }
}

private fun parseSiteVisitDate(value: String?): Date? {
    val cleanDate = value?.trim()?.takeIf { DATE_PATTERN.matches(it) } ?: return null
    val parser = SimpleDateFormat("yyyy-MM-dd", Locale.ROOT).apply {
        isLenient = false
        timeZone = TimeZone.getDefault()
    }
    val position = ParsePosition(0)
    return parser.parse(cleanDate, position)?.takeIf { position.index == cleanDate.length }
}

private fun parseSiteVisitTime(value: String?): Date? {
    val cleanTime = value?.trim()?.takeIf { TIME_PATTERN.matches(it) } ?: return null
    val pattern = if (cleanTime.length == 5) "HH:mm" else "HH:mm:ss"
    val parser = SimpleDateFormat(pattern, Locale.ROOT).apply {
        isLenient = false
        timeZone = TimeZone.getTimeZone("UTC")
    }
    val position = ParsePosition(0)
    return parser.parse(cleanTime, position)?.takeIf { position.index == cleanTime.length }
}

private val DATE_PATTERN = Regex("\\d{4}-\\d{2}-\\d{2}")
private val TIME_PATTERN = Regex("(?:[01]\\d|2[0-3]):[0-5]\\d(?::[0-5]\\d)?")
