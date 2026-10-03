package com.mdavari.vpn.model

/**
 * یک سرور SSTP/OpenVPN.
 * «latency» پینگ واقعیِ اندازه‌گیری‌شده توسط خود برنامه است و «pingMs» پینگ اعلامی منبع.
 */
data class Server(
    val host: String,
    var port: Int = 443,
    var country: String = "",
    var pingMs: Int? = null,
    var latency: Double? = null,
    var alive: Boolean? = null,
    var source: String = ""
) {
    val key: String get() = "$host:$port"

    val label: String get() = if (port == 443) host else "$host:$port"

    val countryFa: String get() {
        val c = country.trim()
        if (c.isEmpty()) return "نامشخص"
        return COUNTRIES_FA[c] ?: c
    }

    val pingText: String get() {
        val lat = latency
        if (lat != null) return "${lat.toInt()} ms"
        val p = pingMs
        if (p != null) return "$p ms"
        return "—"
    }

    companion object {
        val COUNTRIES_FA: Map<String, String> = mapOf(
            "Japan" to "ژاپن",
            "Republic of Korea" to "کره جنوبی",
            "Korea Republic of" to "کره جنوبی",
            "Thailand" to "تایلند",
            "Russian Federation" to "روسیه",
            "Vietnam" to "ویتنام",
            "Viet Nam" to "ویتنام",
            "United States" to "آمریکا",
            "USA" to "آمریکا",
            "Brazil" to "برزیل",
            "Iran" to "ایران",
            "Ukraine" to "اوکراین",
            "Kazakhstan" to "قزاقستان",
            "Indonesia" to "اندونزی",
            "Taiwan" to "تایوان",
            "Hong Kong" to "هنگ‌کنگ",
            "India" to "هند",
            "Turkey" to "ترکیه",
            "France" to "فرانسه",
            "Germany" to "آلمان",
            "United Kingdom" to "انگلستان",
            "Netherlands" to "هلند",
            "Canada" to "کانادا",
            "Singapore" to "سنگاپور",
            "Romania" to "رومانی",
            "Moldova" to "مولداوی",
            "Bulgaria" to "بلغارستان",
            "Poland" to "لهستان",
            "China" to "چین",
            "Croatia" to "کرواسی",
            "Sweden" to "سوئد",
            "Norway" to "نروژ",
            "Finland" to "فینلاند",
            "Switzerland" to "سوئیس",
            "Austria" to "اتریش",
            "Czech Republic" to "چک",
            "Hungary" to "مجارستان",
            "Spain" to "اسپانیا",
            "Italy" to "ایتالیا",
            "Australia" to "استرالیا",
            "South Africa" to "آفریقای جنوبی",
            "Mongolia" to "مغولستان",
            "Israel" to "اسرائیل",
            "Saudi Arabia" to "عربستان",
            "United Arab Emirates" to "امارات"
        )
    }
}
