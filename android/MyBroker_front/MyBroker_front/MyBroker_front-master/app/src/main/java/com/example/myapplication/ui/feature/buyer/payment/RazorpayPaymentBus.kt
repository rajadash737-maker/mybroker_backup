package com.example.myapplication.ui.feature.buyer.payment

import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow

data class RazorpayPaymentResult(
    val success: Boolean,
    val paymentId: String? = null,
    val orderId: String? = null,
    val signature: String? = null,
    val errorMessage: String? = null
)

object RazorpayPaymentBus {
    private val _events = MutableSharedFlow<RazorpayPaymentResult>(
        extraBufferCapacity = 1,
        onBufferOverflow = BufferOverflow.DROP_OLDEST
    )

    val events: SharedFlow<RazorpayPaymentResult> = _events.asSharedFlow()

    fun emit(result: RazorpayPaymentResult) {
        _events.tryEmit(result)
    }
}
