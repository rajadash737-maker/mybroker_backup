package com.example.myapplication.ui.feature.home.profile


import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AlternateEmail
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.graphics.vector.ImageVector
//import androidx.compose.ui.unit.sp
import coil.compose.rememberAsyncImagePainter
import com.example.myapplication.R
import android.content.Context
import android.widget.Toast
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.TextStyle
import com.example.myapplication.network.ApiClient
import com.example.myapplication.ui.feature.buyer.profile.missingBuyerOfferProfileFields
import com.example.myapplication.ui.feature.common.NoInternetContent
import com.example.myapplication.ui.feature.common.rememberIsConnected
import com.example.myapplication.utils.DateUtils
import kotlinx.coroutines.launch

import android.app.DatePickerDialog
import java.util.Calendar






//import com.example.myapplication.ui.theme.home.profile.UploadImageToServer









@Composable
fun EditProfileScreen(
    onSaveClick: () -> Unit = {},
    onBackClick: () -> Unit = {},
    returnToOfferAfterSave: Boolean = false,
    returnToSiteVisitAfterSave: Boolean = false,
    onSiteVisitSaveClick: () -> Unit = {}
) {

    val isConnected by rememberIsConnected()
    var retryTick by remember { mutableStateOf(0) }

    val scroll = rememberScrollState()

    var fullName by remember { mutableStateOf("") }
    var userName by remember { mutableStateOf("") }
    var email by remember { mutableStateOf("") }
    var mobile by remember { mutableStateOf("") }
    var address by remember { mutableStateOf("") }
    var dob by remember { mutableStateOf("") }
    var gender by remember { mutableStateOf("Male") }
//    var profileImageName by remember { mutableStateOf("") }
    var showDobPicker by remember { mutableStateOf(false) }
    var profileImageUrl by remember { mutableStateOf<String?>(null) }
    var validationErrors by remember { mutableStateOf<Map<String, String>>(emptyMap()) }
    var isSaving by remember { mutableStateOf(false) }




    // ----------------- BACKEND VARIABLES -----------------
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    val api = remember(context) {
        ApiClient.init(context.applicationContext)
        ApiClient.apiService
    }

    if (!isConnected) {
        NoInternetContent(
            onRetry = { retryTick++ },
            modifier = Modifier.fillMaxSize()
        )
        return
    }


    // ----------------- AUTO LOAD PROFILE FROM BACKEND -----------------
    LaunchedEffect(isConnected, retryTick) {
        if (!isConnected) return@LaunchedEffect
        try {
            val res = api.getMyProfile()
            val err = res.errorBody()?.string()

            if (res.isSuccessful) {
                val p = res.body() ?: return@LaunchedEffect
                fullName = p.fullname ?: ""
                userName = p.username ?: ""
                email = p.email ?: ""
                mobile = p.mobile ?: ""
                address = p.address ?: ""
                dob = DateUtils.apiToUi(p.dateOfBirth)
                gender = (p.gender ?: "male").replaceFirstChar { it.uppercase() }
                profileImageUrl = p.profileImageUrl
            } else {
                Toast.makeText(context, "Load failed: ${res.code()} ${err ?: ""}", Toast.LENGTH_LONG).show()
            }
        } catch (e: Exception) {
            Toast.makeText(context, "Load error: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }


    val saveChanges: () -> Unit = {
        if (!isSaving) scope.launch {
            val validation = buildProfileUpdateRequest(
                fullname = fullName, username = userName, email = email,
                mobile = mobile, address = address, dateOfBirth = dob, gender = gender
            )
            validationErrors = validation.errors
            val req = validation.request
            if (req != null) {
                isSaving = true
                try {
                    val res = api.updateMyProfile(req)
                    if (res.isSuccessful) {
                        validationErrors = emptyMap()
                        Toast.makeText(context, "Profile updated", Toast.LENGTH_SHORT).show()
                        if (returnToOfferAfterSave || returnToSiteVisitAfterSave) {
                            val refreshed = api.getMyProfile()
                            val profile = refreshed.body().takeIf { refreshed.isSuccessful }
                            if (profile == null) {
                                Toast.makeText(context, "Profile saved, but could not verify it. Please try again.", Toast.LENGTH_LONG).show()
                            } else {
                                val missing = missingBuyerOfferProfileFields(profile)
                                if (missing.isEmpty()) {
                                    if (returnToSiteVisitAfterSave) onSiteVisitSaveClick() else onSaveClick()
                                }
                                else Toast.makeText(context, "Profile is still incomplete. Missing: ${missing.joinToString(", ")}", Toast.LENGTH_LONG).show()
                            }
                        }
                    } else if (res.code() == 422) {
                        validationErrors = profileUpdate422Errors(res.errorBody()?.string())
                    } else {
                        Toast.makeText(context, "Profile update failed (${res.code()}). Please try again.", Toast.LENGTH_LONG).show()
                    }
                } catch (e: Exception) {
                    Toast.makeText(context, "Profile update failed. Check your connection and try again.", Toast.LENGTH_LONG).show()
                } finally {
                    isSaving = false
                }
            }
        }
    }

    Scaffold(
        modifier = Modifier.fillMaxSize().imePadding(),
        containerColor = com.example.myapplication.ui.feature.appBackgroundColor(Color(0xFFF2F5FA)),
        contentWindowInsets = WindowInsets(0, 0, 0, 0),
        bottomBar = {
            Surface(color = MaterialTheme.colorScheme.surface, shadowElevation = 8.dp) {
                Column(Modifier.fillMaxWidth().navigationBarsPadding().padding(horizontal = 16.dp, vertical = 10.dp)) {
                    validationErrors["_form"]?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(bottom = 6.dp)) }
                    Button(
                        onClick = saveChanges, enabled = !isSaving,
                        modifier = Modifier.fillMaxWidth().height(54.dp),
                        shape = RoundedCornerShape(16.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1769D2))
                    ) {
                        if (isSaving) {
                            CircularProgressIndicator(modifier = Modifier.size(20.dp), color = Color.White, strokeWidth = 2.dp)
                            Spacer(Modifier.width(10.dp))
                            Text("Saving...", fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                        } else Text(stringResource(id = R.string.edit_profile_save_changes), fontSize = 17.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    ) { contentPadding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(contentPadding).statusBarsPadding()
                .verticalScroll(scroll).padding(horizontal = 16.dp, vertical = 14.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            ProfileImageSection(
                initialImageUrl = profileImageUrl, userName = fullName, userEmail = email,
                onImageUploaded = { profileImageUrl = it }
            )
            ProfileSectionCard("Personal Information") {
                ProfileInputField(stringResource(id = R.string.edit_profile_full_name), fullName, Icons.Default.Person, validationErrors["fullname"]) {
                    fullName = it; validationErrors = validationErrors - "fullname" - "_form"
                }
                ProfileInputField(stringResource(id = R.string.edit_profile_username), userName, Icons.Default.AlternateEmail, validationErrors["username"]) {
                    userName = it; validationErrors = validationErrors - "username" - "_form"
                }
                ProfileInputField(stringResource(id = R.string.edit_profile_email), email, Icons.Default.Email, validationErrors["email"]) {
                    email = it; validationErrors = validationErrors - "email" - "_form"
                }
                ProfileInputField(stringResource(id = R.string.edit_profile_mobile_number), mobile, Icons.Default.Phone, validationErrors["mobile"]) {
                    mobile = it; validationErrors = validationErrors - "mobile" - "_form"
                }
            }
            ProfileSectionCard("Additional Information") {
                ProfileInputField(stringResource(id = R.string.edit_profile_address), address, Icons.Default.LocationOn, validationErrors["address"]) {
                    address = it; validationErrors = validationErrors - "address" - "_form"
                }
                DobField(value = dob, errorMessage = validationErrors["date_of_birth"], onClick = { showDobPicker = true })
                Text(stringResource(id = R.string.edit_profile_gender), fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = if (com.example.myapplication.ui.feature.isDarkAppTheme()) MaterialTheme.colorScheme.onSurfaceVariant else Color(0xFF536174))
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                    GenderOption(stringResource(id = R.string.gender_male), gender) { gender = it; validationErrors = validationErrors - "gender" - "_form" }
                    GenderOption(stringResource(id = R.string.gender_female), gender) { gender = it; validationErrors = validationErrors - "gender" - "_form" }
                    GenderOption(stringResource(id = R.string.gender_other), gender) { gender = it; validationErrors = validationErrors - "gender" - "_form" }
                }
                validationErrors["gender"]?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
            }
        }
    }

    if (showDobPicker) {
        val calendar = Calendar.getInstance()
        DatePickerDialog(
            context,
            { _, year, month, dayOfMonth ->
                dob = "%02d/%02d/%04d".format(dayOfMonth, month + 1, year)
                validationErrors = validationErrors - "date_of_birth" - "_form"
                showDobPicker = false
            },
            calendar.get(Calendar.YEAR), calendar.get(Calendar.MONTH), calendar.get(Calendar.DAY_OF_MONTH)
        ).apply { datePicker.maxDate = System.currentTimeMillis() }.show()
    }
}

// PROFILE IMAGE
// ============================================================================


@Composable
fun ProfileImageSection(
    initialImageUrl: String?,
    userName: String = "",
    userEmail: String = "",
    onImageUploaded: (String) -> Unit
) {

    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var imageUri by remember { mutableStateOf<Uri?>(null) }
    var serverImage by remember { mutableStateOf<String?>(null) }

    // Priority: fresh API image -> shared pref fallback
    LaunchedEffect(initialImageUrl) {
        val prefs = context.getSharedPreferences("user", Context.MODE_PRIVATE)
        val cached = prefs.getString("PROFILE_IMAGE", null)

        serverImage = when {
            !initialImageUrl.isNullOrBlank() -> initialImageUrl
            !cached.isNullOrBlank() -> cached
            else -> null
        }
    }


    val launcher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        imageUri = uri

        if (uri != null) {
            scope.launch {
                val prefs = context.getSharedPreferences("user", Context.MODE_PRIVATE)

                UploadImageToServer.uploadProfileImage(
                    context = context,
                    uri = uri
                ) { imageUrl ->
                    serverImage = imageUrl

                    prefs.edit()
                        .putString("PROFILE_IMAGE", imageUrl)
                        .apply()

                    onImageUploaded(imageUrl)
                }
            }
        }

    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 3.dp)
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.fillMaxWidth().padding(vertical = 18.dp, horizontal = 16.dp)
        ) {

        // --- DISPLAY FROM BACKEND IF AVAILABLE ---
        val imageModel = when {
            imageUri != null -> imageUri
            !serverImage.isNullOrBlank() -> ApiClient.absoluteUrl(serverImage) ?: serverImage
            else -> null
        }

        Box(contentAlignment = Alignment.BottomEnd) {
            Box(
                modifier = Modifier.size(90.dp).shadow(5.dp, CircleShape).clip(CircleShape)
                    .background(MaterialTheme.colorScheme.surface).clickable { launcher.launch("image/*") },
                contentAlignment = Alignment.Center
            ) {
                if (imageModel != null) {
                    Image(
                        painter = rememberAsyncImagePainter(imageModel),
                        contentDescription = "Profile photo",
                        contentScale = ContentScale.Crop,
                        modifier = Modifier.fillMaxSize().padding(3.dp).clip(CircleShape)
                    )
                } else {
                    Image(
                        painter = painterResource(id = R.drawable.ic_user),
                        contentDescription = "Profile photo",
                        contentScale = ContentScale.Crop,
                        modifier = Modifier.fillMaxSize().padding(3.dp).clip(CircleShape)
                    )
                }
            }
            Surface(
                modifier = Modifier.size(30.dp).clickable { launcher.launch("image/*") },
                shape = CircleShape,
                color = Color(0xFF1769D2),
                border = androidx.compose.foundation.BorderStroke(2.dp, Color.White),
                shadowElevation = 2.dp
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(Icons.Default.CameraAlt, contentDescription = "Change photo", tint = Color.White, modifier = Modifier.size(16.dp))
                }
            }
        }

        Spacer(Modifier.height(10.dp))
        Text(userName.ifBlank { "Your profile" }, fontSize = 19.sp, fontWeight = FontWeight.Bold, color = if (com.example.myapplication.ui.feature.isDarkAppTheme()) MaterialTheme.colorScheme.onSurface else Color(0xFF172B4D), maxLines = 1)
        if (userEmail.isNotBlank()) {
            Text(userEmail, fontSize = 13.sp, color = if (com.example.myapplication.ui.feature.isDarkAppTheme()) MaterialTheme.colorScheme.onSurfaceVariant else Color(0xFF68778D), maxLines = 1)
        }

        TextButton(onClick = { launcher.launch("image/*") }) {
            Text(stringResource(id = R.string.edit_profile_change_photo))
        }
        }
    }
}


// ============================================================================
// INPUT FIELD
// ============================================================================
@Composable
private fun ProfileSectionCard(title: String, content: @Composable ColumnScope.() -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 3.dp)
    ) {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
            Text(title, fontSize = 17.sp, fontWeight = FontWeight.Bold, color = if (com.example.myapplication.ui.feature.isDarkAppTheme()) MaterialTheme.colorScheme.onSurface else Color(0xFF172B4D))
            content()
        }
    }
}

@Composable
fun ProfileInputField(
    label: String,
    value: String,
    icon: ImageVector,
    errorMessage: String? = null,
    onValueChange: (String) -> Unit
) {
    Column(Modifier.fillMaxWidth()) {
        Text(label, fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = if (com.example.myapplication.ui.feature.isDarkAppTheme()) MaterialTheme.colorScheme.onSurfaceVariant else Color(0xFF536174))
        Spacer(Modifier.height(5.dp))
        TextField(
            value = value,
            onValueChange = onValueChange,
            singleLine = true,
            isError = errorMessage != null,
            modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp),
            shape = RoundedCornerShape(15.dp),
            leadingIcon = { Icon(icon, contentDescription = null, tint = Color(0xFF6482A8), modifier = Modifier.size(20.dp)) },
            colors = TextFieldDefaults.colors(
                focusedContainerColor = com.example.myapplication.ui.feature.appSurfaceColor(Color(0xFFF1F5FA)),
                unfocusedContainerColor = com.example.myapplication.ui.feature.appSurfaceColor(Color(0xFFF1F5FA)),
                errorContainerColor = MaterialTheme.colorScheme.errorContainer,
                focusedIndicatorColor = Color.Transparent,
                unfocusedIndicatorColor = Color.Transparent,
                errorIndicatorColor = Color.Transparent,
                cursorColor = if (com.example.myapplication.ui.feature.isDarkAppTheme()) MaterialTheme.colorScheme.primary else Color(0xFF1769D2)
            ),
            textStyle = TextStyle(fontSize = 15.sp, color = if (com.example.myapplication.ui.feature.isDarkAppTheme()) MaterialTheme.colorScheme.onSurface else Color(0xFF172B4D), fontWeight = FontWeight.Medium)
        )
        errorMessage?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(start = 4.dp, top = 3.dp)) }
    }
}


//
//================CHALANDER========================
//


@Composable
fun DobField(
    value: String,
    errorMessage: String? = null,
    onClick: () -> Unit
) {
    Column(Modifier.fillMaxWidth()) {
        Text(stringResource(id = R.string.edit_profile_dob_label), fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = if (com.example.myapplication.ui.feature.isDarkAppTheme()) MaterialTheme.colorScheme.onSurfaceVariant else Color(0xFF536174))
        Spacer(Modifier.height(5.dp))
        Row(
            modifier = Modifier.fillMaxWidth().height(56.dp).clip(RoundedCornerShape(15.dp))
                .background(com.example.myapplication.ui.feature.appSurfaceColor(Color(0xFFF1F5FA))).clickable { onClick() }.padding(horizontal = 14.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(Icons.Default.CalendarMonth, contentDescription = null, tint = Color(0xFF6482A8), modifier = Modifier.size(20.dp))
            Spacer(Modifier.width(12.dp))
            Text(
                text = if (value.isBlank()) stringResource(id = R.string.edit_profile_select_date) else value,
                fontSize = 15.sp, fontWeight = FontWeight.Medium,
                color = if (value.isBlank()) {
                    if (com.example.myapplication.ui.feature.isDarkAppTheme()) MaterialTheme.colorScheme.onSurfaceVariant else Color(0xFF75849A)
                } else if (com.example.myapplication.ui.feature.isDarkAppTheme()) MaterialTheme.colorScheme.onSurface else Color(0xFF172B4D)
            )
        }
        errorMessage?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(start = 4.dp, top = 3.dp)) }
    }
}


// ============================================================================
// GENDER OPTION
// ============================================================================
@Composable
fun GenderOption(
    option: String,
    selectedGender: String,
    onSelect: (String) -> Unit
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .clickable { onSelect(option) }
            .padding(4.dp)
    ) {
        RadioButton(
            selected = selectedGender == option,
            onClick = { onSelect(option) }
        )
        Spacer(modifier = Modifier.width(4.dp))
        Text(option)
    }


 }

//
//@Preview(showBackground = true, showSystemUi = true)
//@Composable
//fun EditProfileScreenPreview() {
//    EditProfileScreen()
//}
