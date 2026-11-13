package com.example.mybroker_admin.domain.repository

import com.example.mybroker_admin.domain.model.RegistryAssignment
import okhttp3.MultipartBody

interface RegistryAssignmentRepository {
    suspend fun getAssignments(skip: Int = 0, limit: Int = 20): List<RegistryAssignment>

    suspend fun getAssignment(bookingId: String): RegistryAssignment?

    suspend fun startVisit(bookingId: String): RegistryAssignment?

    suspend fun completeTask(bookingId: String): RegistryAssignment?

    suspend fun uploadProofs(
        bookingId: String,
        parts: List<MultipartBody.Part>,
        notes: String? = null
    ): RegistryAssignment?

    suspend fun scheduleRegistry(
        bookingId: String,
        date: String,
        time: String,
        location: String,
        fieldOfficerId: Int? = null
    ): RegistryAssignment?
}
