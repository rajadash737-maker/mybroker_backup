package com.example.mybroker_admin.data.repository



import com.example.mybroker_admin.domain.model.LoginResult

interface AuthRepository {
    suspend fun login(identifier: String, password: String): LoginResult
}
