package com.example.myapplication.ui.feature.home.profile

import android.content.Context
import android.content.res.Configuration
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.first
import java.util.Locale

private val Context.languageStore by preferencesDataStore(name = "language_preferences")

object LanguagePreferences {
    const val ENGLISH = "en"
    const val HINDI = "hi"
    private val languageKey = stringPreferencesKey("language_code")

    fun languageFlow(context: Context): Flow<String> = context.languageStore.data.map { it[languageKey] ?: ENGLISH }
    fun selectedLanguageFlow(context: Context): Flow<String> = languageFlow(context)

    suspend fun setLanguage(context: Context, languageCode: String) {
        context.languageStore.edit { it[languageKey] = if (languageCode == HINDI) HINDI else ENGLISH }
        applyLanguage(context, languageCode)
    }

    suspend fun applySavedLanguage(context: Context) {
        val code = languageFlow(context).first()
        applyLanguage(context, code)
    }

    private fun applyLanguage(context: Context, code: String) {
        val locale = Locale(if (code == HINDI) HINDI else ENGLISH)
        Locale.setDefault(locale)
        val configuration = Configuration(context.resources.configuration).apply { setLocale(locale) }
        context.resources.updateConfiguration(configuration, context.resources.displayMetrics)
    }
}
