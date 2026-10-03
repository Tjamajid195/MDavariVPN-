package com.mdavari.vpn.util

/** ابزارهای قالب‌بندی فارسی. */
object Fmt {

    private val FA = charArrayOf('۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹')

    fun fa(input: Any?): String {
        val s = input?.toString() ?: ""
        val sb = StringBuilder(s.length)
        for (c in s) {
            sb.append(if (c in '0'..'9') FA[c - '0'] else c)
        }
        return sb.toString()
    }

    fun clock(seconds: Long): String {
        val sec = if (seconds < 0) 0 else seconds
        val h = sec / 3600
        val m = (sec % 3600) / 60
        val s = sec % 60
        return String.format("%02d:%02d:%02d", h, m, s)
    }

    fun now(): String = String.format("%02d:%02d:%02d",
        java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY),
        java.util.Calendar.getInstance().get(java.util.Calendar.MINUTE),
        java.util.Calendar.getInstance().get(java.util.Calendar.SECOND))
}
