package com.example.mybroker_admin.feature.fieldofficer.dashboard.components


import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.mybroker_admin.feature.fieldofficer.model.FieldCaseUiModel
import kotlinx.coroutines.delay


@Composable
fun ActiveCaseCard(
    case: FieldCaseUiModel,
    onRelease: () -> Unit,
    onClick: () -> Unit
) {

    var remainingTime by remember { mutableStateOf("") }

    LaunchedEffect(case.lockExpiryTime) {
        while (true) {
            val diff = (case.lockExpiryTime ?: 0L) - System.currentTimeMillis()
            if (diff <= 0) {
                remainingTime = "Expired"
                break
            }
            val hours = diff / (1000 * 60 * 60)
            val minutes = (diff / (1000 * 60)) % 60
            remainingTime = "${hours}h ${minutes}m left"
            delay(60000)
        }
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() },
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(Modifier.padding(16.dp)) {

            Text("🔒 Active Case", fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(8.dp))
            Text("Seller: ${case.sellerName}")
            Text("Location: ${case.districtState}")
            Text("Pincode: ${case.pincode}")
            Text("Time: $remainingTime")

            Spacer(modifier = Modifier.height(8.dp))

            Button(onClick = onRelease) {
                Text("Release Case")
            }
        }
    }
}
