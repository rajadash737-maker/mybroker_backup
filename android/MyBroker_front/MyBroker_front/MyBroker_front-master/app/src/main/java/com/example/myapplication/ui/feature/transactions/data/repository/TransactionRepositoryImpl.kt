package com.example.myapplication.ui.feature.transactions.data.repository

import com.example.myapplication.network.ApiClient
import com.example.myapplication.ui.feature.transactions.data.remote.TransactionDto

class TransactionRepositoryImpl {
    suspend fun list(): List<TransactionDto> {
        val response = ApiClient.apiService.getMyTransactions()
        if (!response.isSuccessful) error("Unable to load transactions (${response.code()})")
        return response.body()?.data.orEmpty()
    }

    suspend fun detail(id: String): TransactionDto {
        val response = ApiClient.apiService.getTransactionDetail(id)
        if (!response.isSuccessful) error("Unable to load transaction (${response.code()})")
        return response.body() ?: error("Transaction response was empty")
    }
}
