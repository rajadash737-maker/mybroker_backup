package com.example.mybroker_admin.notification

import android.content.Context
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

data class NotificationItem(
    val id: Int? = null,
    val title: String,
    val body: String,
    val type: String?,
    val propertyId: String?,
    val timestamp: Long,
    val isRead: Boolean = false
)

object NotificationStore {
    private const val PREF_NAME = "mybroker_admin_notifications"
    private const val KEY_ITEMS = "items"
    private const val KEY_READ_PROPERTY_IDS = "read_property_ids"
    private const val MAX_ITEMS = 100
    private val gson = Gson()
    private val _version = MutableStateFlow(0)
    val version = _version.asStateFlow()

    fun load(context: Context): List<NotificationItem> {
        val prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        val raw = prefs.getString(KEY_ITEMS, null) ?: return emptyList()
        return runCatching {
            val type = object : TypeToken<List<NotificationItem>>() {}.type
            gson.fromJson<List<NotificationItem>>(raw, type) ?: emptyList()
        }.getOrElse { emptyList() }
    }

    fun add(context: Context, item: NotificationItem) {
        val readPropertyIds = loadReadPropertyIds(context)
        val propertyId = item.propertyId?.trim().orEmpty()
        val shouldMarkRead = propertyId.isNotEmpty() && readPropertyIds.contains(propertyId)
        val items = load(context).toMutableList()
        if (propertyId.isNotEmpty()) {
            val exists = items.any { it.propertyId?.trim().orEmpty() == propertyId && it.type == item.type }
            if (exists) {
                return
            }
        }
        items.add(0, item.copy(isRead = shouldMarkRead))
        if (items.size > MAX_ITEMS) {
            items.subList(MAX_ITEMS, items.size).clear()
        }
        save(context, items)
        touch()
    }

    fun upsertAll(context: Context, incoming: List<NotificationItem>) {
        if (incoming.isEmpty()) return
        val existing = load(context).toMutableList()
        val byId = existing.associateBy { it.id ?: -1 }.toMutableMap()

        for (item in incoming) {
            val key = item.id ?: -1
            if (key > 0) {
                byId[key] = item
            } else {
                existing.add(item)
            }
        }

        val merged = byId.values
            .sortedByDescending { it.timestamp }
            .toMutableList()

        if (merged.size > MAX_ITEMS) {
            merged.subList(MAX_ITEMS, merged.size).clear()
        }
        save(context, merged)
        touch()
    }

    fun clear(context: Context) {
        val prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        prefs.edit()
            .remove(KEY_ITEMS)
            .remove(KEY_READ_PROPERTY_IDS)
            .apply()
        touch()
    }

    fun unreadCount(context: Context): Int {
        return load(context).count { !it.isRead }
    }

    fun loadAll(context: Context): List<NotificationItem> {
        return load(context)
    }

    fun loadUnread(context: Context): List<NotificationItem> {
        return load(context).filter { !it.isRead }
    }

    fun markReadByTimestamp(context: Context, timestamp: Long) {
        val items = load(context).map { item ->
            if (item.timestamp == timestamp) item.copy(isRead = true) else item
        }
        save(context, items)
        touch()
    }

    fun markReadByPropertyId(context: Context, propertyId: String) {
        if (propertyId.isBlank()) return
        addReadPropertyIds(context, listOf(propertyId))
        val items = load(context).map { item ->
            if (item.propertyId == propertyId) item.copy(isRead = true) else item
        }
        save(context, items)
        touch()
        NotificationSync.markRead(context, referenceIds = listOf(propertyId))
    }

    fun markRead(context: Context, item: NotificationItem) {
        item.id?.let { id ->
            NotificationSync.markRead(context, notificationIds = listOf(id))
        }
        val propertyId = item.propertyId?.trim()
        if (!propertyId.isNullOrEmpty()) {
            markReadByPropertyId(context, propertyId)
        } else {
            markReadByTimestamp(context, item.timestamp)
        }
    }

    fun applyReadPropertyIds(context: Context, propertyIds: List<String>) {
        if (propertyIds.isEmpty()) return
        addReadPropertyIds(context, propertyIds)
        val propertySet = loadReadPropertyIds(context)
        val items = load(context).map { item ->
            val pid = item.propertyId?.trim().orEmpty()
            if (pid.isNotEmpty() && propertySet.contains(pid)) item.copy(isRead = true) else item
        }
        save(context, items)
        touch()
    }

    fun cleanupDuplicates(context: Context) {
        val items = load(context)
        if (items.isEmpty()) return
        val seen = mutableSetOf<String>()
        val deduped = items.filter { item ->
            val pid = item.propertyId?.trim().orEmpty()
            if (pid.isEmpty()) {
                true
            } else {
                val key = "${item.type.orEmpty()}::$pid"
                if (seen.contains(key)) {
                    false
                } else {
                    seen.add(key)
                    true
                }
            }
        }
        if (deduped.size != items.size) {
            save(context, deduped)
            touch()
        }
    }

    private fun loadReadPropertyIds(context: Context): Set<String> {
        val prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        val raw = prefs.getString(KEY_READ_PROPERTY_IDS, null) ?: return emptySet()
        return runCatching {
            val type = object : TypeToken<List<String>>() {}.type
            val list = gson.fromJson<List<String>>(raw, type) ?: emptyList()
            list.mapNotNull { it?.trim() }.filter { it.isNotEmpty() }.toSet()
        }.getOrElse { emptySet() }
    }

    private fun addReadPropertyIds(context: Context, propertyIds: List<String>) {
        val cleaned = propertyIds.mapNotNull { it?.trim() }.filter { it.isNotEmpty() }
        if (cleaned.isEmpty()) return
        val current = loadReadPropertyIds(context).toMutableSet()
        current.addAll(cleaned)
        val prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        prefs.edit().putString(KEY_READ_PROPERTY_IDS, gson.toJson(current.toList())).apply()
    }

    fun markAllRead(context: Context) {
        val items = load(context).map { it.copy(isRead = true) }
        save(context, items)
        touch()
        val propertyIds = items.mapNotNull { it.propertyId?.trim() }.filter { it.isNotEmpty() }
        if (propertyIds.isNotEmpty()) {
            addReadPropertyIds(context, propertyIds)
            NotificationSync.markRead(context, referenceIds = propertyIds)
        }
        NotificationSync.markAllRead(context)
    }

    private fun save(context: Context, items: List<NotificationItem>) {
        val prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        prefs.edit().putString(KEY_ITEMS, gson.toJson(items)).apply()
    }

    private fun touch() {
        _version.value = _version.value + 1
    }
}
