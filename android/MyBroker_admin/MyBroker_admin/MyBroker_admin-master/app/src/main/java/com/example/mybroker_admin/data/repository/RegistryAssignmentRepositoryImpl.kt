package com.example.mybroker_admin.data.repository

import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.remote.api.AdminListingApi
import com.example.mybroker_admin.data.remote.api.FieldOfficerApi
import com.example.mybroker_admin.data.remote.dto.AdminBookingFieldOfficerUpdateRequestDto
import com.example.mybroker_admin.data.remote.dto.AdminRegistryScheduleRequestDto
import com.example.mybroker_admin.data.remote.dto.FieldOfficerRegistryAssignmentDetailDto
import com.example.mybroker_admin.data.remote.dto.FieldOfficerRegistryAssignmentItemDto
import com.example.mybroker_admin.domain.model.RegistryAssignment
import com.example.mybroker_admin.domain.model.RegistryStatus
import com.example.mybroker_admin.domain.repository.RegistryAssignmentRepository
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody

class RegistryAssignmentRepositoryImpl(
    private val fieldOfficerApi: FieldOfficerApi,
    private val adminListingApi: AdminListingApi
) : RegistryAssignmentRepository {

    override suspend fun getAssignments(skip: Int, limit: Int): List<RegistryAssignment> {
        val response = fieldOfficerApi.getRegistryAssignments(skip = skip, limit = limit)
        return response.items.map { it.toDomain() }
    }

    override suspend fun getAssignment(bookingId: String): RegistryAssignment? {
        val id = bookingId.toIntOrNull() ?: return null
        val response = fieldOfficerApi.getRegistryAssignmentDetail(id)
        return response.assignment.toDomain()
    }

    override suspend fun startVisit(bookingId: String): RegistryAssignment? {
        val id = bookingId.toIntOrNull() ?: return null
        val response = fieldOfficerApi.startRegistryVisit(id)
        return response.assignment.toDomain()
    }

    override suspend fun completeTask(bookingId: String): RegistryAssignment? {
        val id = bookingId.toIntOrNull() ?: return null
        fieldOfficerApi.completeRegistry(id)
        return getAssignment(bookingId)
    }

    override suspend fun uploadProofs(
        bookingId: String,
        parts: List<MultipartBody.Part>,
        notes: String?
    ): RegistryAssignment? {
        val id = bookingId.toIntOrNull() ?: return null
        val notesBody: RequestBody? = notes?.takeIf { it.isNotBlank() }?.toRequestBody()
        fieldOfficerApi.uploadRegistryProofs(id, parts, notesBody)
        return getAssignment(bookingId)
    }

    override suspend fun scheduleRegistry(
        bookingId: String,
        date: String,
        time: String,
        location: String,
        fieldOfficerId: Int?
    ): RegistryAssignment? {
        val id = bookingId.toIntOrNull() ?: return null
        fieldOfficerId?.let {
            adminListingApi.updateBookingFieldOfficer(
                id = id,
                body = AdminBookingFieldOfficerUpdateRequestDto(field_officer_id = it)
            )
        }
        adminListingApi.scheduleRegistry(
            id = id,
            body = AdminRegistryScheduleRequestDto(
                registry_date = date,
                registry_time = time,
                registry_location = location
            )
        )
        return getAssignment(bookingId)
    }

    private fun FieldOfficerRegistryAssignmentItemDto.toDomain(): RegistryAssignment {
        return RegistryAssignment(
            id = booking_id.toString(),
            listingId = listing_id,
            dealAmount = deal_amount,
            propertyName = property_name ?: "-",
            propertyType = property_type ?: "-",
            propertyArea = property_area ?: "-",
            propertyAddress = property_address ?: "-",
            buyerName = buyer_name,
            sellerName = seller_name ?: "-",
            buyerPhone = buyer_mobile,
            sellerPhone = seller_mobile ?: "-",
            date = registry_date ?: "",
            time = registry_time ?: "",
            location = registry_location ?: "",
            status = status.toRegistryStatus(),
            assignedOfficer = assigned_officer_name ?: "",
            proofUrls = emptyList()
        )
    }

    private fun FieldOfficerRegistryAssignmentDetailDto.toDomain(): RegistryAssignment {
        val urls = proofs.mapNotNull { ApiClient.absoluteUrl(it.file_url) }
        return RegistryAssignment(
            id = booking_id.toString(),
            listingId = listing_id,
            dealAmount = deal_amount,
            propertyName = property_name ?: "-",
            propertyType = property_type ?: "-",
            propertyArea = property_area ?: "-",
            propertyAddress = property_address ?: "-",
            buyerName = buyer_name,
            sellerName = seller_name ?: "-",
            buyerPhone = buyer_mobile,
            sellerPhone = seller_mobile ?: "-",
            date = registry_date ?: "",
            time = registry_time ?: "",
            location = registry_location ?: "",
            status = status.toRegistryStatus(),
            assignedOfficer = assigned_officer_name ?: "",
            proofUrls = urls
        )
    }

    private fun String.toRegistryStatus(): RegistryStatus {
        return when (this.lowercase()) {
            "registry_scheduled" -> RegistryStatus.SCHEDULED
            "in_process" -> RegistryStatus.IN_PROGRESS
            "registry_done" -> RegistryStatus.COMPLETED
            "sold" -> RegistryStatus.COMPLETED
            else -> RegistryStatus.BOOKED
        }
    }
}
