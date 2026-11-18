package com.example.myapplication.ui.feature.sitevisit.presentation

import java.time.LocalDate
import java.time.LocalTime
import java.time.format.DateTimeFormatter

internal object SiteVisitBookingTime {
    val hours: List<String> = (9..17).map { it.toString().padStart(2, '0') }
    val minutes: List<String> = (0..59).map { it.toString().padStart(2, '0') }
    private val dateFormatter = DateTimeFormatter.ISO_LOCAL_DATE

    fun formatDate(date: LocalDate): String = date.format(dateFormatter)

    fun isDateAllowed(date: LocalDate, today: LocalDate): Boolean = !date.isBefore(today)

    fun timeFor(hour: String, minute: String): LocalTime? {
        if (hour !in hours || minute !in minutes) return null
        return LocalTime.of(hour.toInt(), minute.toInt())
    }

    fun isTimeAllowed(date: LocalDate, time: LocalTime, today: LocalDate, now: LocalTime): Boolean =
        time in LocalTime.of(9, 0)..LocalTime.of(17, 59) && (date != today || time.isAfter(now))

    fun validate(dateText: String, hour: String?, minute: String?, today: LocalDate, now: LocalTime): String? {
        val date = runCatching { LocalDate.parse(dateText, dateFormatter) }.getOrNull()
            ?: return "Select a valid visit date."
        if (!isDateAllowed(date, today)) return "Visit date cannot be in the past."
        if (hour == null || minute == null) return "Select both an hour and minute."
        val time = timeFor(hour, minute) ?: return "Select a visit time between 09:00 and 17:59."
        if (!isTimeAllowed(date, time, today, now)) {
            return if (date == today) "Select a future time between 09:00 and 17:59." else "Select a time between 09:00 and 17:59."
        }
        return null
    }
}
