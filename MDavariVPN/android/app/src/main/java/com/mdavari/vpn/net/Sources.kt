package com.mdavari.vpn.net

import android.content.Context
import android.util.Base64
import com.mdavari.vpn.model.Server
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.File
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.InetAddress
import java.net.URL
import java.util.zip.GZIPInputStream

/**
 * گرفتن لیست سرورها از چند منبع (همان معماری نسخه‌ی ویندوز):
 *  ۱) خود سایت ipspeed.info با هدر مرورگر واقعی
 *  ۲) همان سایت از مسیر خواندنی r.jina.ai
 *  ۳) API رسمی VPN Gate  (همان سرورها + کانفیگ OpenVPN)
 *  ۴) آینه‌های گیت‌هاب
 *  ۵) کف آخر: کش محلی
 */
object Sources {

    private const val UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

    private val SITE_URLS = listOf(
        "https://ipspeed.info/free-sstp.php",
        "https://m.ipspeed.info/freevpn_sstp.php?language=en"
    )
    private const val JINA = "https://r.jina.ai/"
    private const val VPNGATE = "https://www.vpngate.net/api/iphone/"
    private val MIRRORS = listOf(
        "https://raw.githubusercontent.com/Koros0111/Vpn-Gate-SSTP/main/sstp_hosts.txt",
        "https://raw.githubusercontent.com/Delta-Kronecker/Vpn-Gate/main/sstp_hosts.txt"
    )

    private val HOST_RE = Regex("([A-Za-z0-9][A-Za-z0-9.\\-]*\\.opengw\\.net)(?::(\\d{1,5}))?")
    private val PING_RE = Regex("([\\d,]{1,7})\\s*ms", RegexOption.IGNORE_CASE)

    data class Result(
        val servers: List<Server>,
        val ovpnConfigs: Map<String, String>,
        val report: String
    )

    // ------------------------------------------------------------------
    // HTTP
    // ------------------------------------------------------------------
    fun httpGet(url: String, timeoutMs: Int = 20000): Pair<Int, String> {
        var conn: HttpURLConnection? = null
        return try {
            conn = (URL(url).openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = timeoutMs
                readTimeout = timeoutMs
                instanceFollowRedirects = true
                setRequestProperty("User-Agent", UA)
                setRequestProperty("Accept", "text/html,application/xhtml+xml,*/*;q=0.8")
                setRequestProperty("Accept-Language", "en-US,en;q=0.9,fa;q=0.8")
                setRequestProperty("Accept-Encoding", "gzip")
            }
            val code = conn.responseCode
            val stream = if (code in 200..299) conn.inputStream else conn.errorStream
            val text = stream?.let { readAll(it, conn.contentEncoding) } ?: ""
            code to text
        } catch (e: Exception) {
            -1 to "__ERROR__ ${e.message}"
        } finally {
            try {
                conn?.disconnect()
            } catch (_: Exception) {
            }
        }
    }

    private fun readAll(stream: java.io.InputStream, encoding: String?): String {
        val input = if (encoding != null && encoding.contains("gzip", true))
            GZIPInputStream(stream) else stream
        val reader = BufferedReader(InputStreamReader(input, Charsets.UTF_8))
        val sb = StringBuilder()
        var line = reader.readLine()
        while (line != null) {
            sb.append(line).append('\n')
            line = reader.readLine()
        }
        reader.close()
        return sb.toString()
    }

    private fun looksLikeChallenge(text: String): Boolean {
        val head = text.take(6000).lowercase()
        return head.contains("just a moment") || head.contains("cf-mitigated") ||
                head.contains("cf-chl") || head.contains("enable javascript and cookies")
    }

    // ------------------------------------------------------------------
    // پارس
    // ------------------------------------------------------------------
    private fun stripTags(chunk: String): String =
        chunk.replace(Regex("<[^>]+>"), " ")
            .replace("&nbsp;", " ")
            .replace("&amp;", "&")
            .replace("&zwnj;", "\u200c")
            .replace(Regex("\\s+"), " ")
            .trim()

    fun detectCountry(row: String): String {
        val low = row.lowercase()
        val table = listOf(
            "Japan" to listOf("japan", "ژاپن"),
            "Republic of Korea" to listOf("korea", "کره"),
            "Thailand" to listOf("thailand", "تایلند"),
            "Russian Federation" to listOf("russia", "روسیه"),
            "Vietnam" to listOf("viet nam", "vietnam", "ویتنام"),
            "United States" to listOf("united states", "america", "آمریکا", "usa"),
            "Brazil" to listOf("brazil", "برزیل"),
            "Iran" to listOf("iran", "ایران"),
            "Ukraine" to listOf("ukraine", "اوکراین"),
            "Kazakhstan" to listOf("kazakhstan"),
            "Indonesia" to listOf("indonesia"),
            "Taiwan" to listOf("taiwan"),
            "Hong Kong" to listOf("hong kong"),
            "India" to listOf("india"),
            "Turkey" to listOf("turkey"),
            "France" to listOf("france"),
            "Germany" to listOf("germany"),
            "United Kingdom" to listOf("united kingdom", "england", "london"),
            "Netherlands" to listOf("netherlands"),
            "Canada" to listOf("canada"),
            "Singapore" to listOf("singapore"),
            "Romania" to listOf("romania"),
            "Moldova" to listOf("moldova"),
            "Bulgaria" to listOf("bulgaria"),
            "Poland" to listOf("poland"),
            "China" to listOf("china"),
            "Croatia" to listOf("croatia"),
            "Sweden" to listOf("sweden"),
            "Norway" to listOf("norway"),
            "Finland" to listOf("finland"),
            "Switzerland" to listOf("switzerland"),
            "Austria" to listOf("austria"),
            "Czech Republic" to listOf("czech"),
            "Hungary" to listOf("hungary"),
            "Spain" to listOf("spain"),
            "Italy" to listOf("italy"),
            "Australia" to listOf("australia"),
            "South Africa" to listOf("south africa"),
            "Mongolia" to listOf("mongolia"),
            "Israel" to listOf("israel")
        )
        for ((name, keys) in table) {
            for (k in keys) if (low.contains(k)) return name
        }
        return ""
    }

    fun parseServers(text: String, source: String): List<Server> {
        val out = ArrayList<Server>()
        val rows: List<String> = if (text.contains("<tr", true) || text.contains("<table", true)) {
            text.replace(Regex("</tr>"), "\n", RegexOption.IGNORE_CASE)
                .split("\n").map { stripTags(it) }.filter { it.isNotEmpty() }
        } else {
            text.split("\n").map { it.trim() }.filter { it.isNotEmpty() }
        }
        for (row in rows) {
            val matches = HOST_RE.findAll(row)
            for (m in matches) {
                val host = m.groupValues[1]
                val port = m.groupValues[2].toIntOrNull() ?: 443
                val ping = PING_RE.find(row)?.groupValues?.get(1)?.replace(",", "")?.toIntOrNull()
                out.add(
                    Server(
                        host = host,
                        port = if (port in 1..65535) port else 443,
                        country = detectCountry(row),
                        pingMs = ping,
                        source = source
                    )
                )
            }
        }
        return out
    }

    // ------------------------------------------------------------------
    // منابع
    // ------------------------------------------------------------------
    private fun fetchSites(log: (String) -> Unit, viaJina: Boolean): List<Server> {
        for (url in SITE_URLS) {
            val target = if (viaJina) JINA + url else url
            val (code, text) = httpGet(target, if (viaJina) 40000 else 25000)
            val src = if (viaJina) "ipspeed(jina)" else "ipspeed"
            when {
                looksLikeChallenge(text) ->
                    log("! Cloudflare جلوی درخواست را گرفت (challenge) — $url")
                code == 200 && text.isNotEmpty() -> {
                    val servers = parseServers(text, src)
                    if (servers.isNotEmpty()) {
                        log("✓ لیست از سایت گرفته شد: ${servers.size} سرور")
                        return servers
                    }
                    log("! صفحه باز شد ولی سروری پیدا نشد — $url")
                }
                else -> log("! پاسخ ناموفق از سایت (کد $code) — $url")
            }
        }
        return emptyList()
    }

    private fun fetchVpnGate(log: (String) -> Unit): Pair<List<Server>, Map<String, String>> {
        val (code, text) = httpGet(VPNGATE, 25000)
        if (code != 200 || text.isEmpty()) {
            log("! API ونگیت جواب نداد (کد $code)")
            return emptyList<Server>() to emptyMap()
        }
        val servers = ArrayList<Server>()
        val configs = HashMap<String, String>()
        for (line in text.split("\n")) {
            if (line.isEmpty() || line.startsWith("*") || line.startsWith("#")) continue
            val parts = line.split(",", limit = 15)
            if (parts.size < 6) continue
            var host = parts[0].trim()
            if (host.isEmpty()) continue
            if (!host.contains(".")) host = "$host.opengw.net"
            val ping = parts[3].toDoubleOrNull()?.toInt()
            val country = normalizeCountry(parts[5])
            servers.add(Server(host = host, port = 443, country = country, pingMs = ping,
                source = "vpngate"))
            if (parts.size >= 15) {
                val b64 = parts[14].trim()
                if (b64.isNotEmpty()) {
                    try {
                        val cfg = String(Base64.decode(b64, Base64.DEFAULT), Charsets.UTF_8)
                        if (cfg.contains("remote ")) configs[host] = cfg
                    } catch (_: Exception) {
                    }
                }
            }
        }
        log("✓ منبع VPN Gate: ${servers.size} سرور (${configs.size} کانفیگ OpenVPN)")
        return servers to configs
    }

    private fun normalizeCountry(raw: String): String {
        var c = raw.replace(Regex("\\(.*?\\)"), "").trim()
        c = c.replace(Regex("\\s{2,}"), " ")
        if (c.lowercase().startsWith("korea republic")) return "Republic of Korea"
        return c
    }

    private fun fetchMirrors(log: (String) -> Unit): List<Server> {
        for (url in MIRRORS) {
            val (code, text) = httpGet(url, 20000)
            if (code != 200 || text.contains("__ERROR__")) continue
            val out = ArrayList<Server>()
            for (raw in text.split("\n")) {
                val line = raw.trim()
                if (line.isEmpty() || line.startsWith("#")) continue
                val m = HOST_RE.find(line) ?: continue
                out.add(
                    Server(
                        host = m.groupValues[1],
                        port = m.groupValues[2].toIntOrNull() ?: 443,
                        country = detectCountry(line),
                        source = "mirror"
                    )
                )
            }
            if (out.isNotEmpty()) {
                log("✓ آینه‌ی گیت‌هاب: ${out.size} آدرس")
                return out
            }
        }
        return emptyList()
    }

    // ------------------------------------------------------------------
    // کشوردهی با ip-api (اختیاری)
    // ------------------------------------------------------------------
    private fun geoFill(servers: List<Server>, log: (String) -> Unit, limit: Int = 100) {
        val todo = servers.filter { it.country.isEmpty() }.take(limit)
        if (todo.isEmpty()) return
        try {
            val hosts = LinkedHashMap<String, String>() // host -> ip
            for (s in todo) {
                try {
                    val ip = InetAddress.getByName(s.host).hostAddress ?: continue
                    hosts[s.host] = ip
                } catch (_: Exception) {
                }
            }
            if (hosts.isEmpty()) return
            val uniqueIps = hosts.values.toSet()
            val body = JSONArray().apply { uniqueIps.forEach { add(JSONObject().put("query", it)) } }
            val conn = (URL("http://ip-api.com/batch?fields=query,country").openConnection()
                    as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = 12000
                readTimeout = 12000
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
            }
            conn.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            val code = conn.responseCode
            if (code != 200) return
            val resp = conn.inputStream.bufferedReader().readText()
            val arr = JSONArray(resp)
            val ip2c = HashMap<String, String>()
            for (i in 0 until arr.length()) {
                val o = arr.optJSONObject(i) ?: continue
                ip2c[o.optString("query")] = o.optString("country")
            }
            var filled = 0
            for (s in todo) {
                val c = ip2c[hosts[s.host]] ?: continue
                if (c.isNotEmpty()) {
                    s.country = c
                    filled++
                }
            }
            if (filled > 0) log("@ کشور $filled سرور تکمیل شد")
        } catch (_: Exception) {
        }
    }

    // ------------------------------------------------------------------
    // کش
    // ------------------------------------------------------------------
    private fun cacheFile(ctx: Context) = File(ctx.filesDir, "servers_cache.json")
    private fun ovpnCacheFile(ctx: Context) = File(ctx.filesDir, "ovpn_cache.json")

    fun saveCache(ctx: Context, servers: List<Server>, configs: Map<String, String>) {
        try {
            val arr = JSONArray()
            for (s in servers) {
                arr.put(JSONObject().apply {
                    put("h", s.host); put("p", s.port); put("c", s.country)
                    put("pm", s.pingMs ?: -1); put("src", s.source)
                })
            }
            cacheFile(ctx).writeText(arr.toString(), Charsets.UTF_8)
            if (configs.isNotEmpty()) {
                val o = JSONObject()
                configs.forEach { (k, v) -> o.put(k, v) }
                ovpnCacheFile(ctx).writeText(o.toString(), Charsets.UTF_8)
            }
        } catch (_: Exception) {
        }
    }

    fun loadCache(ctx: Context): Pair<List<Server>, Map<String, String>> {
        val servers = ArrayList<Server>()
        val configs = HashMap<String, String>()
        try {
            val f = cacheFile(ctx)
            if (f.exists()) {
                val arr = JSONArray(f.readText(Charsets.UTF_8))
                for (i in 0 until arr.length()) {
                    val o = arr.optJSONObject(i) ?: continue
                    val pm = o.optInt("pm", -1)
                    servers.add(
                        Server(
                            host = o.optString("h"),
                            port = o.optInt("p", 443),
                            country = o.optString("c"),
                            pingMs = if (pm >= 0) pm else null,
                            source = o.optString("src")
                        )
                    )
                }
            }
            val g = ovpnCacheFile(ctx)
            if (g.exists()) {
                val o = JSONObject(g.readText(Charsets.UTF_8))
                val it = o.keys()
                while (it.hasNext()) {
                    val k = it.next()
                    configs[k] = o.optString(k)
                }
            }
        } catch (_: Exception) {
        }
        return servers to configs
    }

    // ------------------------------------------------------------------
    // اصلی
    // ------------------------------------------------------------------
    fun refresh(ctx: Context, log: (String) -> Unit): Result {
        log("… شروع دریافت لیست سرورها")
        val all = ArrayList<Server>()
        var configs = HashMap<String, String>()
        val report = StringBuilder()

        val site = try {
            fetchSites(log, viaJina = false)
        } catch (e: Exception) {
            log("! خطای سایت: ${e.message}"); emptyList<Server>()
        }
        if (site.isNotEmpty()) {
            all.addAll(site); report.append("site:${site.size} ")
        } else {
            val jina = try {
                fetchSites(log, viaJina = true)
            } catch (e: Exception) {
                emptyList<Server>()
            }
            if (jina.isNotEmpty()) {
                all.addAll(jina); report.append("site-alt:${jina.size} ")
            }
        }

        try {
            val (vg, cfg) = fetchVpnGate(log)
            if (vg.isNotEmpty()) {
                all.addAll(vg); configs = HashMap(cfg); report.append("vpngate:${vg.size} ")
            }
        } catch (e: Exception) {
            log("! خطای ونگیت: ${e.message}")
        }

        try {
            val mir = fetchMirrors(log)
            if (mir.isNotEmpty()) {
                all.addAll(mir); report.append("mirror:${mir.size} ")
            }
        } catch (e: Exception) {
            log("! خطای آینه‌ها: ${e.message}")
        }

        // ادغام
        val merged = LinkedHashMap<String, Server>()
        for (s in all) {
            val cur = merged[s.key]
            if (cur == null) {
                merged[s.key] = s
            } else {
                if (cur.country.isEmpty() && s.country.isNotEmpty()) cur.country = s.country
                if (cur.pingMs == null && s.pingMs != null) cur.pingMs = s.pingMs
                if (s.source.isNotEmpty() && !cur.source.contains(s.source)) {
                    cur.source = "${cur.source}+${s.source}"
                }
            }
        }
        var servers = merged.values.toList()

        if (servers.isEmpty()) {
            val (cached, cfg) = loadCache(ctx)
            if (cached.isNotEmpty()) {
                log("~ استفاده از لیست ذخیره‌شده‌ی قبلی: ${cached.size} سرور")
                return Result(cached, cfg, "cache:${cached.size}")
            }
            log("✗ هیچ منبعی جواب نداد و کش هم خالی است")
            return Result(emptyList(), emptyMap(), "empty")
        }

        geoFill(servers, log)
        servers = servers.sortedBy { it.pingMs ?: 99999 }
        saveCache(ctx, servers, configs)
        log("# مجموع: ${servers.size} سرور یکتا  ($report)")
        return Result(servers, configs, report.toString().trim())
    }
}
