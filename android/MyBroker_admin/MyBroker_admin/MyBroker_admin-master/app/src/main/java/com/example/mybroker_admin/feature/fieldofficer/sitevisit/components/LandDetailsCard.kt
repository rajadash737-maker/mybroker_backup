package com.example.mybroker_admin.feature.fieldofficer.sitevisit.components



import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun LandDetailsCard(
    title: String,
    area: String,
    city: String,
    state: String,
    price: String
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = 12.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {

            Text("Land Details", style = MaterialTheme.typography.titleMedium)

            Spacer(modifier = Modifier.height(8.dp))

            Text("Title: $title")
            Text("Area: $area")
            Text("City: $city")
            Text("State: $state")
            Text("Expected Price: $price")
        }
    }
}
