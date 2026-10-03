package com.mdavari.vpn.util

import android.content.Context
import java.util.UUID

/** تنظیمات سبک برنامه روی SharedPreferences. */
class Prefs(ctx: Context) {

    private val sp = ctx.getSharedPreferences("mdavari", Context.MODE_PRIVATE)

    var pingTimeout: Int
        get() = sp.getInt("ping_timeout", 2)
        set(v) = sp.edit().putInt("ping_timeout", v).apply()

    var onlyPort443: Boolean
        get() = sp.getBoolean("only_port_443", true)
        set(v) = sp.edit().putBoolean("only_port_443", v).apply()

    var autoReconnect: Boolean
        get() = sp.getBoolean("auto_reconnect", true)
        set(v) = sp.edit().putBoolean("auto_reconnect", v).apply()

    var autoPingAfterFetch: Boolean
        get() = sp.getBoolean("auto_ping", true)
        set(v) = sp.edit().putBoolean("auto_ping", v).apply()

    var autoOpenClient: Boolean
        get() = sp.getBoolean("auto_open", true)
        set(v) = sp.edit().putBoolean("auto_open", v).apply()

    var l2tpPreferred: Boolean
        get() = sp.getBoolean("l2tp_pref", false)
        set(v) = sp.edit().putBoolean("l2tp_pref", v).apply()

    /** کد یکتای دستگاه (فقط محلی؛ جایی ارسال نمی‌شود). */
    val deviceId: String
        get() {
            val existing = sp.getString("device_id", null)
            if (existing != null && existing.isNotEmpty()) return existing
            val made = "MD-" + UUID.randomUUID().toString().substring(0, 8).uppercase()
            sp.edit().putString("device_id", made).apply()
            return made
        }

    fun clearCache() {
        sp.edit().remove("last_list_time").apply()
    }
}
