package com.example.myapplication.ui.feature.home.profile

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.datastore.preferences.core.Preferences
import com.example.myapplication.ui.feature.BrokerSurfaceAlt
import com.example.myapplication.ui.feature.BrokerSurfaceDark
import com.example.myapplication.ui.feature.BrokerTextDark
import com.example.myapplication.ui.feature.appColorScheme
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class ThemePreferenceTest {
    @Test
    fun profileAndSettingsSwitchesReadAndWriteTheSamePreference() = runBlocking {
        val dataStore = newDataStore()
        val profileTheme = ThemeRepository(dataStore)
        val settingsTheme = ThemeRepository(dataStore)

        assertFalse(profileTheme.isDark.first())
        profileTheme.setDark(true)

        assertTrue(settingsTheme.isDark.first())
        settingsTheme.setDark(false)
        assertFalse(profileTheme.isDark.first())
    }

    @Test
    fun selectedThemePersistsInDataStore() = runBlocking {
        val dataStore = newDataStore()
        ThemeRepository(dataStore).setDark(true)

        // A newly created repository over the persisted store observes the saved choice.
        assertTrue(ThemeRepository(dataStore).isDark.first())
    }

    @Test
    fun colorSchemeSelectionKeepsLightPaletteAndUsesDarkSurfacesAndText() {
        val light = appColorScheme(darkTheme = false)
        val dark = appColorScheme(darkTheme = true)

        assertEquals(BrokerSurfaceAlt, light.background)
        assertEquals(BrokerSurfaceDark, dark.background)
        assertEquals(BrokerTextDark, dark.onSurface)
        assertTrue(dark.surface != light.surface)
    }

    private fun newDataStore(): DataStore<Preferences> {
        val file = File.createTempFile("mybrokerr-theme", ".preferences_pb").apply { delete() }
        return PreferenceDataStoreFactory.create(
            scope = CoroutineScope(SupervisorJob() + Dispatchers.IO),
            produceFile = { file }
        )
    }
}
