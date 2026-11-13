package com.example.myapplication.notification

import android.content.Context
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import org.json.JSONArray
import org.json.JSONObject

object NotificationStore {
    private const val PREFS = "user_notifications"
    private const val ITEMS = "items"
    private val _version = MutableStateFlow(0)
    val version: StateFlow<Int> = _version

    @Synchronized
    fun load(context: Context): List<NotificationItem> {
        val raw = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(ITEMS, "[]") ?: "[]"
        return runCatching {
            val array = JSONArray(raw)
            (0 until array.length()).mapNotNull { index ->
                val item = array.optJSONObject(index) ?: return@mapNotNull null
                NotificationItem(
                    id = item.optInt("id").takeIf { item.has("id") && !item.isNull("id") },
                    title = item.optString("title"),
                    body = item.optString("body"),
                    type = item.optString("type").takeIf(String::isNotEmpty),
                    referenceId = item.optString("referenceId").takeIf(String::isNotEmpty),
                    roleTarget = item.optString("roleTarget").takeIf(String::isNotEmpty),
                    timestamp = item.optLong("timestamp"),
                    isRead = item.optBoolean("isRead")
                )
            }
        }.getOrDefault(emptyList())
    }

    @Synchronized
    fun upsertAll(context: Context, items: List<NotificationDto>) {
        val merged = (items.map(::toItem) + load(context)).distinctBy { it.id ?: it.referenceId ?: "${it.title}:${it.timestamp}" }
            .sortedByDescending(NotificationItem::timestamp)
        save(context, merged)
    }

    fun add(context: Context, item: NotificationItem) = upsert(context, item)

    @Synchronized
    fun markRead(context: Context, item: NotificationItem) {
        save(context, load(context).map { if (it.id == item.id && it.referenceId == item.referenceId) it.copy(isRead = true) else it })
    }

    @Synchronized
    fun markAllRead(context: Context) = save(context, load(context).map { it.copy(isRead = true) })

    fun unreadCount(context: Context): Int = load(context).count { !it.isRead }

    private fun upsert(context: Context, item: NotificationItem) {
        val existing = load(context)
        val key = item.id?.toString() ?: item.referenceId ?: "${item.title}:${item.timestamp}"
        save(context, (listOf(item) + existing.filter {
            (it.id?.toString() ?: it.referenceId ?: "${it.title}:${it.timestamp}") != key
        }).sortedByDescending(NotificationItem::timestamp))
    }

    private fun toItem(dto: NotificationDto) = NotificationItem(
        id = dto.id, title = dto.title, body = dto.body, type = dto.type,
        referenceId = dto.referenceId, roleTarget = dto.roleTarget,
        timestamp = dto.createdAt?.let { runCatching { java.time.Instant.parse(it).toEpochMilli() }.getOrNull() }
            ?: System.currentTimeMillis(), isRead = dto.isRead
    )

    private fun save(context: Context, items: List<NotificationItem>) {
        val array = JSONArray()
        items.forEach { item ->
            array.put(JSONObject().apply {
                if (item.id != null) put("id", item.id)
                put("title", item.title); put("body", item.body)
                put("type", item.type); put("referenceId", item.referenceId)
                put("roleTarget", item.roleTarget); put("timestamp", item.timestamp)
                put("isRead", item.isRead)
            })
        }
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(ITEMS, array.toString()).apply()
        _version.value++
    }
}
