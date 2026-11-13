package com.example.mybroker_admin.domain.model

enum class RegistryStatus {
    BOOKED,
    SCHEDULED,
    IN_PROGRESS,
    COMPLETED;

    val displayName: String
        get() = when (this) {
            BOOKED -> "Booked"
            SCHEDULED -> "Scheduled"
            IN_PROGRESS -> "In Progress"
            COMPLETED -> "Completed"
        }
}
