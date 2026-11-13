package com.example.mybroker_admin.feature.admin.listings.presentation

import android.app.DatePickerDialog
import android.app.TimePickerDialog
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import com.example.mybroker_admin.data.remote.dto.AdminFieldOfficerOptionDto
import com.example.mybroker_admin.feature.admin.listings.BookedListingDetailState
import com.example.mybroker_admin.feature.admin.listings.BookedListingDetailViewModel
import com.example.mybroker_admin.feature.admin.listings.BookingDocumentUi
import java.text.SimpleDateFormat
import java.util.Locale

@Composable
fun BookedListingDetailRoute(
    listingId: Int,
    onBack: () -> Unit,
    onViewDocument: (String) -> Unit,
    readOnly: Boolean = false
) {
    val vm: BookedListingDetailViewModel = viewModel()
    val state = vm.state.collectAsState().value

    LaunchedEffect(listingId) {
        if (!state.loaded) vm.load(listingId)
    }

    BookedListingDetailScreen(
        state = state,
        onRetry = { vm.load(listingId) },
        onBack = onBack,
        onViewDocument = onViewDocument,
        onLoadFieldOfficers = vm::loadFieldOfficers,
        onUpdateFieldOfficer = vm::updateFieldOfficer,
        onScheduleRegistry = vm::scheduleRegistry,
        onVerifyRegistry = vm::verifyRegistry,
        readOnly = readOnly
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BookedListingDetailScreen(
    state: BookedListingDetailState,
    onRetry: () -> Unit,
    onBack: () -> Unit,
    onViewDocument: (String) -> Unit,
    onLoadFieldOfficers: () -> Unit,
    onUpdateFieldOfficer: (Int, Int) -> Unit,
    onScheduleRegistry: (Int, String, String, String) -> Unit,
    onVerifyRegistry: (Int, String) -> Unit,
    readOnly: Boolean = false
) {
    val isSheetOpen = remember { mutableStateOf(false) }
    val context = LocalContext.current
    val localError = remember { mutableStateOf<String?>(null) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "Booking Details",
                style = MaterialTheme.typography.headlineMedium
            )
            TextButton(onClick = onBack) { Text("Back") }
        }

        Spacer(modifier = Modifier.height(8.dp))

        when {
            state.isLoading -> {
                Spacer(modifier = Modifier.height(24.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.Center
                ) {
                    CircularProgressIndicator()
                }
            }
            state.error != null -> {
                val errorText: String = state.error ?: "Something went wrong"
                Text(
                    text = errorText,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.error
                )
                Spacer(modifier = Modifier.height(12.dp))
                OutlinedButton(onClick = onRetry) {
                    Text("Retry")
                }
            }
            state.detail == null -> {
                Text(
                    text = "No details available",
                    style = MaterialTheme.typography.bodyMedium
                )
            }
            else -> {
                val detail = state.detail
                val scheduleDate = remember { mutableStateOf("") }
                val scheduleTime = remember { mutableStateOf("") }
                val scheduleLocation = remember { mutableStateOf("") }

                LaunchedEffect(detail.registry?.date) {
                    if (scheduleDate.value.isBlank() && !detail.registry?.date.isNullOrBlank()) {
                        scheduleDate.value = detail.registry?.date ?: ""
                    }
                }
                LaunchedEffect(detail.registry?.time) {
                    if (scheduleTime.value.isBlank() && !detail.registry?.time.isNullOrBlank()) {
                        scheduleTime.value = detail.registry?.time ?: ""
                    }
                }
                LaunchedEffect(detail.registry?.location) {
                    if (scheduleLocation.value.isBlank() && !detail.registry?.location.isNullOrBlank()) {
                        scheduleLocation.value = detail.registry?.location ?: ""
                    }
                }

                LazyColumn(
                    contentPadding = PaddingValues(vertical = 8.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    item {
                        state.message?.let {
                            val messageText: String = it
                            Text(
                                text = messageText,
                                style = MaterialTheme.typography.bodyMedium,
                                color = Color(0xFF1B5E20)
                            )
                        }
                    }
                    item {
                        localError.value?.let { msg ->
                            Text(
                                text = msg,
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.error
                            )
                        }
                    }
                    item {
                        state.error?.let {
                            val errorText: String = it
                            Text(
                                text = errorText,
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.error
                            )
                        }
                    }
                    item {
                        SectionCard(title = "A. Basic Info") {
                            InfoRow(label = "Listing ID", value = detail.listingId.toString())
                            InfoRow(label = "Status", value = detail.status)
                            InfoRow(label = "Booking Status", value = detail.bookingStatus)
                            InfoRow(label = "Booked Date", value = detail.bookedAt ?: "-")
                        }
                    }

                    item {
                        SectionCard(title = "B. Buyer Info") {
                            InfoRow(label = "Name", value = detail.buyer.name)
                            InfoRow(label = "Phone", value = detail.buyer.mobile ?: "-")
                            DocumentList(
                                title = "Buyer Documents",
                                documents = detail.buyer.documents,
                                onViewDocument = onViewDocument
                            )
                        }
                    }

                    item {
                        SectionCard(title = "B. Seller Info") {
                            InfoRow(label = "Name", value = detail.seller.name)
                            InfoRow(label = "Phone", value = detail.seller.mobile ?: "-")
                            DocumentList(
                                title = "Seller Documents",
                                documents = detail.seller.documents,
                                onViewDocument = onViewDocument
                            )
                        }
                    }

                    item {
                        SectionCard(title = "C. Land Info") {
                            InfoRow(label = "Expected Price", value = detail.land.expectedPrice ?: "-")
                            InfoRow(label = "Deal Price", value = detail.land.dealPrice ?: "-")
                            InfoRow(label = "Location", value = detail.land.location ?: "-")
                        }
                    }

                    item {
                        SectionCard(title = "D. Payment") {
                            InfoRow(label = "Processing Fee", value = detail.payment.tokenAmount ?: "-")
                            InfoRow(label = "Deal Amount", value = detail.land.dealPrice ?: "-")
                            StatusRow(label = "Payment Status", value = detail.payment.status ?: "-")
                        }
                    }

                    item {
                        SectionCard(title = "E. Field Officer") {
                            val officer = detail.fieldOfficer
                            InfoRow(label = "Name", value = officer?.name ?: "-")
                            InfoRow(label = "Mobile", value = officer?.mobile ?: "-")
                            if (!readOnly) {
                                Spacer(modifier = Modifier.height(10.dp))
                                FilledTonalButton(
                                    onClick = {
                                        onLoadFieldOfficers()
                                        isSheetOpen.value = true
                                    },
                                    modifier = Modifier.fillMaxWidth(),
                                    enabled = !state.isUpdatingOfficer
                                ) {
                                    Text(text = "Change Field Officer")
                                }
                            }
                        }
                    }

                    item {
                        SectionCard(title = "G. Registry Info") {
                            InfoRow(label = "Registry Date", value = formatDate(detail.registry?.date))
                            InfoRow(label = "Registry Time", value = formatTime(detail.registry?.time))
                            InfoRow(label = "Location", value = detail.registry?.location ?: "-")
                            InfoRow(label = "Registry Status", value = detail.registry?.status ?: "-")
                            Spacer(modifier = Modifier.height(8.dp))
                            if (!readOnly) {
                                val datePicker = remember {
                                    DatePickerDialog(
                                        context,
                                        { _, y, m, d ->
                                            scheduleDate.value = String.format("%04d-%02d-%02d", y, m + 1, d)
                                        },
                                        2026,
                                        0,
                                        1
                                    )
                                }
                                val timePicker = remember {
                                    TimePickerDialog(
                                        context,
                                        { _, h, min ->
                                            scheduleTime.value = String.format("%02d:%02d:00", h, min)
                                        },
                                        10,
                                        0,
                                        true
                                    )
                                }

                                InfoRowClickable(
                                    label = "Pick Date",
                                    value = formatDate(scheduleDate.value).ifBlank { "Select" },
                                    onClick = { datePicker.show() }
                                )
                                InfoRowClickable(
                                    label = "Pick Time",
                                    value = formatTime(scheduleTime.value).ifBlank { "Select" },
                                    onClick = { timePicker.show() }
                                )
                                OutlinedTextField(
                                    value = scheduleLocation.value,
                                    onValueChange = { scheduleLocation.value = it },
                                    label = { Text("Registry Location") },
                                    modifier = Modifier.fillMaxWidth()
                                )
                                Spacer(modifier = Modifier.height(8.dp))

                                FilledTonalButton(
                                    onClick = {
                                        val bookingId = detail.bookingId
                                        if (scheduleDate.value.isBlank() || scheduleTime.value.isBlank() || scheduleLocation.value.isBlank()) {
                                            localError.value = "Please select date, time, and location before scheduling."
                                        } else {
                                            localError.value = null
                                            onScheduleRegistry(bookingId, scheduleDate.value, scheduleTime.value, scheduleLocation.value)
                                        }
                                    },
                                    modifier = Modifier.fillMaxWidth(),
                                    enabled = !state.isUpdatingRegistry
                                ) {
                                    Text(text = "Schedule Registry")
                                }
                            }

                            val proofs = detail.registry?.proofs ?: emptyList()
                            if (proofs.isNotEmpty()) {
                                DocumentList(
                                    title = "Registry Proofs",
                                    documents = proofs,
                                    onViewDocument = onViewDocument
                                )
                            }

                            if (!readOnly && detail.bookingStatus == "REGISTRY DONE") {
                                Spacer(modifier = Modifier.height(8.dp))
                                FilledTonalButton(
                                    onClick = { onVerifyRegistry(detail.bookingId, "approve") },
                                    modifier = Modifier.fillMaxWidth(),
                                    enabled = !state.isUpdatingRegistry
                                ) {
                                    Text(text = "Approve & Mark Sold")
                                }
                                Spacer(modifier = Modifier.height(6.dp))
                                OutlinedButton(
                                    onClick = { onVerifyRegistry(detail.bookingId, "reject") },
                                    modifier = Modifier.fillMaxWidth(),
                                    enabled = !state.isUpdatingRegistry
                                ) {
                                    Text(text = "Reject Verification")
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    if (isSheetOpen.value) {
        val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
        ModalBottomSheet(
            onDismissRequest = { isSheetOpen.value = false },
            sheetState = sheetState
        ) {
            FieldOfficerPickerSheet(
                officers = state.fieldOfficers,
                onSelect = { officer ->
                    val bookingId = state.detail?.bookingId ?: return@FieldOfficerPickerSheet
                    onUpdateFieldOfficer(bookingId, officer.id)
                    isSheetOpen.value = false
                }
            )
        }
    }
}

@Composable
private fun SectionCard(
    title: String,
    content: @Composable () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Text(text = title, style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(8.dp))
            content()
        }
    }
}

@Composable
private fun InfoRow(
    label: String,
    value: String
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(modifier = Modifier.width(12.dp))
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium
        )
    }
}

@Composable
private fun InfoRowClickable(
    label: String,
    value: String,
    onClick: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() },
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(modifier = Modifier.width(12.dp))
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.primary
        )
    }
}

@Composable
private fun StatusRow(
    label: String,
    value: String
) {
    val color = when (value.uppercase()) {
        "SUCCESS" -> Color(0xFF2E7D32)
        "PENDING" -> Color(0xFFED6C02)
        "FAILED" -> Color(0xFFD32F2F)
        else -> MaterialTheme.colorScheme.onSurface
    }
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(modifier = Modifier.width(12.dp))
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium,
            color = color
        )
    }
}

private fun formatDate(raw: String?): String {
    if (raw.isNullOrBlank()) return "-"
    val inputFormats = listOf(
        SimpleDateFormat("yyyy-MM-dd", Locale.ENGLISH),
        SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.ENGLISH)
    )
    val output = SimpleDateFormat("dd MMMM yyyy", Locale.ENGLISH)
    for (fmt in inputFormats) {
        runCatching {
            val date = fmt.parse(raw.trim()) ?: return@runCatching null
            return output.format(date)
        }
    }
    return raw
}

private fun formatTime(raw: String?): String {
    if (raw.isNullOrBlank()) return "-"
    val cleaned = raw.trim().replace("Z", "")
    val inputFormats = listOf(
        SimpleDateFormat("HH:mm:ss", Locale.ENGLISH),
        SimpleDateFormat("HH:mm", Locale.ENGLISH),
        SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.ENGLISH)
    )
    val output = SimpleDateFormat("hh.mm a", Locale.ENGLISH)
    for (fmt in inputFormats) {
        runCatching {
            val date = fmt.parse(cleaned) ?: return@runCatching null
            return output.format(date).replace("AM", "am").replace("PM", "pm")
        }
    }
    return raw
}

@Composable
private fun DocumentList(
    title: String,
    documents: List<BookingDocumentUi>,
    onViewDocument: (String) -> Unit
) {
    Spacer(modifier = Modifier.height(8.dp))
    Text(text = title, style = MaterialTheme.typography.titleSmall)
    if (documents.isEmpty()) {
        Spacer(modifier = Modifier.height(6.dp))
        Text(text = "No documents uploaded", style = MaterialTheme.typography.bodySmall)
        return
    }
    Spacer(modifier = Modifier.height(6.dp))
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        documents.forEach { doc ->
            DocumentRow(document = doc, onViewDocument = onViewDocument)
        }
    }
}

@Composable
private fun DocumentRow(
    document: BookingDocumentUi,
    onViewDocument: (String) -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            if (document.url.endsWith(".jpg", true)
                || document.url.endsWith(".jpeg", true)
                || document.url.endsWith(".png", true)
                || document.url.endsWith(".webp", true)
            ) {
                AsyncImage(
                    model = document.url,
                    contentDescription = document.name,
                    modifier = Modifier
                        .height(36.dp)
                        .width(48.dp),
                    contentScale = ContentScale.Crop
                )
                Spacer(modifier = Modifier.width(8.dp))
            }
            Column {
                Text(text = document.name, style = MaterialTheme.typography.bodyMedium)
                if (!document.createdAt.isNullOrBlank()) {
                    Text(
                        text = "Uploaded: ${document.createdAt}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
        TextButton(onClick = { onViewDocument(document.url) }) {
            Text(text = "View Document")
        }
    }
}

@Composable
private fun FieldOfficerPickerSheet(
    officers: List<AdminFieldOfficerOptionDto>,
    onSelect: (AdminFieldOfficerOptionDto) -> Unit
) {
    Column(modifier = Modifier.padding(16.dp)) {
        Text(
            text = "Select Field Officer",
            style = MaterialTheme.typography.titleMedium
        )
        Spacer(modifier = Modifier.height(12.dp))
        if (officers.isEmpty()) {
            Text(text = "No field officers available", style = MaterialTheme.typography.bodyMedium)
            return
        }
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            officers.forEach { officer ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onSelect(officer) },
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text(text = officer.fullname, style = MaterialTheme.typography.titleSmall)
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = officer.mobile ?: "-",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
        Spacer(modifier = Modifier.height(12.dp))
    }
}
