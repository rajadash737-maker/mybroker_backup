package com.example.myapplication.ui.feature.buyer.profile

import com.example.myapplication.network.UserProfileResponse

/** Fields the buyer must have before the app opens the land offer form. */
fun missingBuyerOfferProfileFields(profile: UserProfileResponse?): List<String> {
    if (profile == null) {
        return listOf("Full Name", "Username", "Email", "Mobile Number", "Address", "Date of Birth")
    }

    return buildList {
        if (profile.fullname.isNullOrBlank()) add("Full Name")
        if (profile.username.isNullOrBlank()) add("Username")
        if (profile.email.isNullOrBlank()) add("Email")
        if (profile.mobile.isNullOrBlank()) add("Mobile Number")
        if (profile.address.isNullOrBlank()) add("Address")
        if (profile.dateOfBirth.isNullOrBlank()) add("Date of Birth")
    }
}
