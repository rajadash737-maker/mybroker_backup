package com.example.mybroker_admin.feature.sitevisit

import java.math.BigDecimal

/** UI-only validation mirrors the existing accounting request constraints. */
fun parseSiteVisitRefundAmountPaise(value: String): Int? = runCatching {
    BigDecimal(value.trim()).movePointRight(2).intValueExact().takeIf { it > 0 }
}.getOrNull()

fun canConfirmSiteVisitRefund(amountPaise: Int?, eligiblePaise: Int, transactionReference: String): Boolean =
    amountPaise != null && amountPaise in 1..eligiblePaise && transactionReference.trim().length >= 6

fun canRecordSiteVisitRefundFailure(reason: String): Boolean = reason.trim().length >= 3

fun canDisplaySiteVisitBuyerUpi(role: String?): Boolean = role.equals("ACCOUNTING", ignoreCase = true)

fun siteVisitRefundStatusColorKey(status: String): String = when (status.lowercase()) {
    "pending_details" -> "awaiting_upi"
    "pending" -> "pending"
    "refunded" -> "refunded"
    "failed" -> "failed"
    else -> "unknown"
}
