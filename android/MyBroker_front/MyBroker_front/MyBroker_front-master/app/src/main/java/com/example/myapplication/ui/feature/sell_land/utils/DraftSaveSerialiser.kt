package com.example.myapplication.ui.feature.sell_land.utils

import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

/** Ensures successive draft saves observe the request ID returned by the prior save. */
class DraftSaveSerialiser {
    private val mutex = Mutex()

    suspend fun <T> run(block: suspend () -> T): T = mutex.withLock { block() }
}
