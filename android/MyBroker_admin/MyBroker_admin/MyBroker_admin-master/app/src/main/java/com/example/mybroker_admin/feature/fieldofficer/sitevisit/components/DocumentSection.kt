package com.example.mybroker_admin.feature.fieldofficer.sitevisit.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.mybroker_admin.data.remote.dto.ListingMediaDto

@Composable
fun DocumentSection(
    documents: List<ListingMediaDto>,
    onViewClick: (String) -> Unit // file_url
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = 12.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = "Documents Uploaded",
                style = MaterialTheme.typography.titleMedium
            )

            Spacer(modifier = Modifier.height(8.dp))

            if (documents.isEmpty()) {
                Text("No documents uploaded")
                return@Column
            }

            documents.forEach { doc ->
                val docName = doc.document_type
                    ?.replace("_", " ")
                    ?.replaceFirstChar { it.uppercase() }
                    ?: doc.file_name

                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 6.dp),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text("✔ $docName")
                    TextButton(onClick = { onViewClick(doc.file_url) }) {
                        Text("View")
                    }
                }
            }
        }
    }
}
