package com.example.mybroker_admin.data.remote.dto

import com.google.gson.Gson
import com.google.gson.JsonNull
import org.junit.Assert.assertEquals
import org.junit.Test

class AdminInstagramRequestSerializationTest {
    @Test fun removeRequestRetainsExplicitJsonNull() {
        val json = Gson().toJson(AdminInstagramUrlUpdateRequestDto(JsonNull.INSTANCE))
        assertEquals("{\"instagram_url\":null}", json)
    }
}
