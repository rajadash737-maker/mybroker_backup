package com.example.mybroker_admin.feature.registry.screens

import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Divider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.example.mybroker_admin.core.components.RegistryStatusChip
import com.example.mybroker_admin.domain.model.RegistryStatus
import com.example.mybroker_admin.feature.registry.RegistryDetailViewModel
import com.example.mybroker_admin.feature.registry.components.RegistryInfoRow
import android.database.Cursor
import android.provider.OpenableColumns
import android.webkit.MimeTypeMap
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File

@Composable
fun RegistryDetailScreen(
    navController: NavController,
    assignmentId: String,
    viewModel: RegistryDetailViewModel = viewModel()
) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current

    LaunchedEffect(assignmentId) {
        viewModel.load(assignmentId)
    }

    LaunchedEffect(state.message) {
        val message = state.message ?: return@LaunchedEffect
        Toast.makeText(context, message, Toast.LENGTH_SHORT).show()
        viewModel.clearMessage()
    }

    val proofLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetMultipleContents()
    ) { uris ->
        val parts = uris.mapNotNull { uri ->
            val mimeType = context.contentResolver.getType(uri)
            uriToTempFile(context, uri, mimeType)?.let { file ->
                val req = file.readBytes().toRequestBody(
                    (mimeType ?: "application/octet-stream").toMediaTypeOrNull()
                )
                MultipartBody.Part.createFormData("files", file.name, req)
            }
        }
        if (parts.isNotEmpty()) {
            viewModel.uploadProofs(parts)
        } else if (uris.isNotEmpty()) {
            Toast.makeText(context, "File read failed", Toast.LENGTH_SHORT).show()
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
            .verticalScroll(rememberScrollState())
    ) {
        TextButton(onClick = { navController.popBackStack() }) {
            Text("Back")
        }

        Spacer(modifier = Modifier.height(8.dp))

        when {
            state.isLoading -> {
                CircularProgressIndicator()
                return@Column
            }
            state.assignment == null -> {
                Text(state.error ?: "Registry assignment not found")
                return@Column
            }
        }

        val assignment = state.assignment
        if (assignment == null) return@Column
        val normalizedAddress = normalizeAddress(assignment.propertyAddress)

        Text(
            text = "Registry Detail",
            style = MaterialTheme.typography.titleLarge
        )

        Spacer(modifier = Modifier.height(12.dp))

        Row(modifier = Modifier.fillMaxWidth()) {
            Text(
                text = assignment.propertyName,
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.weight(1f)
            )
            RegistryStatusChip(status = assignment.status)
        }

        Spacer(modifier = Modifier.height(12.dp))
        Text("Property Details", style = MaterialTheme.typography.titleSmall)
        Spacer(modifier = Modifier.height(8.dp))
        RegistryInfoRow(label = "Type", value = assignment.propertyType)
        Spacer(modifier = Modifier.height(6.dp))
        RegistryInfoRow(label = "Area", value = assignment.propertyArea)
        Spacer(modifier = Modifier.height(6.dp))
        RegistryInfoRow(label = "Address", value = normalizedAddress)
        Spacer(modifier = Modifier.height(6.dp))
        RegistryInfoRow(label = "Deal Amount", value = state.dealAmount ?: "-")

        Spacer(modifier = Modifier.height(16.dp))
        Text("Buyer & Seller", style = MaterialTheme.typography.titleSmall)
        Spacer(modifier = Modifier.height(8.dp))
        RegistryInfoRow(label = "Buyer", value = assignment.buyerName)
        Spacer(modifier = Modifier.height(6.dp))
        RegistryInfoRow(label = "Buyer Phone", value = assignment.buyerPhone)
        Spacer(modifier = Modifier.height(6.dp))
        RegistryInfoRow(label = "Seller", value = assignment.sellerName)
        Spacer(modifier = Modifier.height(6.dp))
        RegistryInfoRow(label = "Seller Phone", value = assignment.sellerPhone)

        Spacer(modifier = Modifier.height(16.dp))
        Text("Registry Schedule", style = MaterialTheme.typography.titleSmall)
        Spacer(modifier = Modifier.height(8.dp))
        RegistryInfoRow(label = "Date", value = assignment.date.ifBlank { "TBD" })
        Spacer(modifier = Modifier.height(6.dp))
        RegistryInfoRow(label = "Time", value = assignment.time.ifBlank { "TBD" })
        Spacer(modifier = Modifier.height(6.dp))
        RegistryInfoRow(label = "Location", value = assignment.location.ifBlank { "TBD" })
        Spacer(modifier = Modifier.height(6.dp))
        RegistryInfoRow(label = "Field Officer", value = assignment.assignedOfficer.ifBlank { "TBD" })

        if (assignment.status == RegistryStatus.BOOKED) {
            Spacer(modifier = Modifier.height(16.dp))
            Divider()
            Spacer(modifier = Modifier.height(12.dp))
            Text("Admin Scheduling", style = MaterialTheme.typography.titleSmall)

            var scheduleDate by remember(assignment.id) { mutableStateOf(assignment.date) }
            var scheduleTime by remember(assignment.id) { mutableStateOf(assignment.time) }
            var scheduleLocation by remember(assignment.id) { mutableStateOf(assignment.location) }
            var officerName by remember(assignment.id) { mutableStateOf(assignment.assignedOfficer) }

            Spacer(modifier = Modifier.height(8.dp))
            OutlinedTextField(
                value = scheduleDate,
                onValueChange = { scheduleDate = it },
                label = { Text("Date (YYYY-MM-DD)") },
                modifier = Modifier.fillMaxWidth()
            )
            Spacer(modifier = Modifier.height(8.dp))
            OutlinedTextField(
                value = scheduleTime,
                onValueChange = { scheduleTime = it },
                label = { Text("Time (HH:MM)") },
                modifier = Modifier.fillMaxWidth()
            )
            Spacer(modifier = Modifier.height(8.dp))
            OutlinedTextField(
                value = scheduleLocation,
                onValueChange = { scheduleLocation = it },
                label = { Text("Registry Location") },
                modifier = Modifier.fillMaxWidth()
            )
            Spacer(modifier = Modifier.height(8.dp))
            OutlinedTextField(
                value = officerName,
                onValueChange = { officerName = it },
                label = { Text("Assign Field Officer ID") },
                modifier = Modifier.fillMaxWidth()
            )
            Spacer(modifier = Modifier.height(12.dp))
            Button(
                onClick = {
                    viewModel.scheduleRegistry(
                        date = scheduleDate,
                        time = scheduleTime,
                        location = scheduleLocation,
                        officer = officerName
                    )
                },
                modifier = Modifier.fillMaxWidth(),
                enabled = scheduleDate.isNotBlank() && scheduleTime.isNotBlank() &&
                    scheduleLocation.isNotBlank() && officerName.isNotBlank()
            ) {
                Text("Schedule Registry")
            }
        }

        Spacer(modifier = Modifier.height(16.dp))
        Divider()
        Spacer(modifier = Modifier.height(12.dp))

        Text("Actions", style = MaterialTheme.typography.titleSmall)
        Spacer(modifier = Modifier.height(8.dp))

        Button(
            onClick = {
                val query = Uri.encode(assignment.location)
                val intent = Intent(
                    Intent.ACTION_VIEW,
                    Uri.parse("geo:0,0?q=$query")
                )
                if (intent.resolveActivity(context.packageManager) != null) {
                    context.startActivity(intent)
                } else {
                    Toast.makeText(context, "No map app found", Toast.LENGTH_SHORT).show()
                }
            },
            modifier = Modifier.fillMaxWidth(),
            enabled = assignment.location.isNotBlank()
        ) {
            Text("Open Map")
        }

        Spacer(modifier = Modifier.height(8.dp))

        Button(
            onClick = { proofLauncher.launch("*/*") },
            modifier = Modifier.fillMaxWidth(),
            enabled = assignment.status != RegistryStatus.COMPLETED
        ) {
            val label = if (assignment.proofUrls.isEmpty()) "Upload Proofs" else "Upload More Proofs"
            Text(label)
        }

        Spacer(modifier = Modifier.height(8.dp))

        if (assignment.status == RegistryStatus.SCHEDULED) {
            Button(
                onClick = { viewModel.startVisit() },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Start Visit")
            }
            Spacer(modifier = Modifier.height(8.dp))
        }

        if (assignment.status == RegistryStatus.IN_PROGRESS) {
            Button(
                onClick = { viewModel.completeTask() },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Complete Task")
            }
            Spacer(modifier = Modifier.height(8.dp))
        }

        if (assignment.status == RegistryStatus.COMPLETED) {
            Text("Task completed. Proofs uploaded: ${assignment.proofUrls.size}")
        }

        if (state.isSubmitting) {
            Spacer(modifier = Modifier.height(12.dp))
            CircularProgressIndicator()
        }

        state.error?.let {
            Spacer(modifier = Modifier.height(12.dp))
            Text(it, color = MaterialTheme.colorScheme.error)
        }
    }
}

private fun uriToTempFile(
    context: android.content.Context,
    uri: Uri,
    mimeType: String?
): File? {
    return try {
        val input = context.contentResolver.openInputStream(uri) ?: return null
        val extension = resolveExtension(context, uri, mimeType)
        val suffix = if (extension.isNotBlank()) ".$extension" else ""
        val file = File.createTempFile("registry_", suffix, context.cacheDir)
        input.use { ins -> file.outputStream().use { outs -> ins.copyTo(outs) } }
        file
    } catch (_: Exception) {
        null
    }
}

private fun resolveExtension(
    context: android.content.Context,
    uri: Uri,
    mimeType: String?
): String {
    val name = queryDisplayName(context, uri)
    val nameExt = name?.substringAfterLast('.', "")
    if (!nameExt.isNullOrBlank()) return nameExt.lowercase()

    val mimeExt = MimeTypeMap.getSingleton().getExtensionFromMimeType(mimeType)
    return mimeExt?.lowercase().orEmpty()
}

private fun queryDisplayName(context: android.content.Context, uri: Uri): String? {
    val projection = arrayOf(OpenableColumns.DISPLAY_NAME)
    val cursor: Cursor? = context.contentResolver.query(uri, projection, null, null, null)
    cursor.use { cur ->
        if (cur != null && cur.moveToFirst()) {
            val idx = cur.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (idx >= 0) return cur.getString(idx)
        }
    }
    return null
}

private fun normalizeAddress(rawAddress: String): String {
    val tokens = rawAddress
        .split(",")
        .map { it.trim() }
        .filter { it.isNotBlank() }

    val unique = ArrayList<String>(tokens.size)
    for (token in tokens) {
        if (!unique.contains(token)) unique.add(token)
    }
    return unique.joinToString(", ").ifBlank { "-" }
}
