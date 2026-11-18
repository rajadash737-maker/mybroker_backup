package com.example.myapplication.ui.feature.home_pase

import android.content.Context
import com.example.myapplication.network.ApiClient
import com.example.myapplication.network.SessionManager
import com.example.myapplication.ui.feature.buyer.data.remote.dto.IncomingOfferCountDto
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class OfferBadgeState(
    val count: Int? = null,
    val isLoading: Boolean = false,
    val hasError: Boolean = false
)

fun formatOfferBadgeCount(count: Int): String? = when {
    count <= 0 -> null
    count > 99 -> "99+"
    else -> count.toString()
}

fun incomingOfferBadgeCount(counts: IncomingOfferCountDto): Int =
    (counts.seller_pending.coerceAtLeast(0) + counts.buyer_countered.coerceAtLeast(0))

object IncomingOfferCountStore {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private val mutableState = MutableStateFlow(OfferBadgeState())
    val state = mutableState.asStateFlow()
    private var requestInFlight = false
    private var ownerId: Int? = null
    private var appContext: Context? = null

    @Synchronized
    fun refresh(context: Context? = null) {
        if (context != null) appContext = context.applicationContext
        val requestContext = appContext ?: return
        val session = SessionManager(requestContext)
        val currentOwner = session.getUserId()
        if (currentOwner != ownerId) {
            ownerId = currentOwner
            mutableState.value = OfferBadgeState()
        }
        if (currentOwner == null || requestInFlight) return
        requestInFlight = true
        mutableState.value = mutableState.value.copy(isLoading = true, hasError = false)
        scope.launch {
            runCatching {
                ApiClient.init(requestContext)
                incomingOfferBadgeCount(ApiClient.apiService.getIncomingOfferCount())
            }.onSuccess { count ->
                mutableState.value = OfferBadgeState(count = count.coerceAtLeast(0))
            }.onFailure {
                mutableState.value = OfferBadgeState(hasError = true)
            }
            synchronized(this@IncomingOfferCountStore) { requestInFlight = false }
        }
    }
}
