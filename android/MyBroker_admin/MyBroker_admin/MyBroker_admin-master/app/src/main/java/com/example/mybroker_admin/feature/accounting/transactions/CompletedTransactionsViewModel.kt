package com.example.mybroker_admin.feature.accounting.transactions

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.data.remote.dto.AccountingCompletedTransactionItemDto
import com.example.mybroker_admin.data.remote.dto.AccountingPaymentDetailsDto
import com.example.mybroker_admin.data.repository.AccountingListingRepository
import com.example.mybroker_admin.feature.accounting.transactions.model.PaymentDetails
import com.example.mybroker_admin.feature.accounting.transactions.model.PaymentInfo
import com.example.mybroker_admin.feature.accounting.transactions.model.Transaction
import com.example.mybroker_admin.feature.accounting.transactions.model.TransactionDetail
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class CompletedTransactionsViewModel : ViewModel() {

    private val repo = AccountingListingRepository(ApiClient.accountingListingApi)

    private val _transactions = MutableStateFlow<List<Transaction>>(emptyList())
    val transactions: StateFlow<List<Transaction>> = _transactions.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    private val _detail = MutableStateFlow<TransactionDetail?>(null)
    val detail: StateFlow<TransactionDetail?> = _detail.asStateFlow()

    private val _detailLoading = MutableStateFlow(false)
    val detailLoading: StateFlow<Boolean> = _detailLoading.asStateFlow()

    private val _detailError = MutableStateFlow<String?>(null)
    val detailError: StateFlow<String?> = _detailError.asStateFlow()

    init {
        loadTransactions()
    }

    fun loadTransactions() = viewModelScope.launch {
        _isLoading.value = true
        _errorMessage.value = null

        runCatching { repo.getCompletedTransactions(skip = 0, limit = 50) }
            .onSuccess { res ->
                _transactions.value = res.items.map { mapTransaction(it) }
            }
            .onFailure { err ->
                _errorMessage.value = err.message ?: "Failed to load completed transactions"
            }

        _isLoading.value = false
    }

    fun loadTransactionDetail(listingId: String) = viewModelScope.launch {
        val listingNumericId = listingId.toIntOrNull()
        if (listingNumericId == null) {
            _detailError.value = "Invalid listing id"
            return@launch
        }

        _detailLoading.value = true
        _detailError.value = null

        runCatching { repo.getCompletedTransactionDetail(listingNumericId) }
            .onSuccess { res ->
                val tx = mapTransaction(res.transaction)
                _detail.value = TransactionDetail(
                    transaction = tx,
                    landPriceNote = res.land_price_note,
                    finalStatus = res.final_status,
                    paymentDetails = mapPaymentDetails(res.payment_details)
                )
            }
            .onFailure { err ->
                _detailError.value = err.message ?: "Failed to load transaction detail"
            }

        _detailLoading.value = false
    }

    private fun mapTransaction(dto: AccountingCompletedTransactionItemDto): Transaction {
        return Transaction(
            listingId = dto.listing_id.toString(),
            sellerName = dto.seller_name,
            sellerFee = dto.seller_fee,
            sellerFeeStatus = dto.seller_fee_status,
            buyerName = dto.buyer_name,
            buyerFee = dto.buyer_fee,
            buyerFeeStatus = dto.buyer_fee_status,
            status = dto.status,
            date = dto.date
        )
    }

    private fun mapPaymentDetails(dto: AccountingPaymentDetailsDto?): PaymentDetails {
        val seller = dto?.seller?.let {
            PaymentInfo(
                method = it.method,
                transactionId = it.transaction_id,
                paidAt = it.paid_at,
                status = it.status
            )
        }
        val buyer = dto?.buyer?.let {
            PaymentInfo(
                method = it.method,
                transactionId = it.transaction_id,
                paidAt = it.paid_at,
                status = it.status
            )
        }
        return PaymentDetails(seller = seller, buyer = buyer)
    }
}
