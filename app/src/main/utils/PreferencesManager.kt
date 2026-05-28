package com.iptv.player.utils

import android.content.Context
import android.content.SharedPreferences

object PreferencesManager {
    private const val PREF_NAME = "iptv_prefs"
    private const val KEY_LAST_CHANNEL_INDEX = "last_channel_index"

    private fun getPrefs(context: Context): SharedPreferences {
        return context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
    }

    fun saveLastChannelIndex(context: Context, index: Int) {
        getPrefs(context).edit().putInt(KEY_LAST_CHANNEL_INDEX, index).apply()
    }

    fun getLastChannelIndex(context: Context, default: Int = 0): Int {
        return getPrefs(context).getInt(KEY_LAST_CHANNEL_INDEX, default)
    }
}
