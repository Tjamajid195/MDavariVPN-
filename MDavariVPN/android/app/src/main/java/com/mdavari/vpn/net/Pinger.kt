package com.mdavari.vpn.net

import android.os.Handler
import android.os.Looper
import com.mdavari.vpn.model.Server
import java.net.HttpURLConnection
import java.net.InetSocketAddress
import java.net.Socket
import java.net.URL
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicInteger

/** تست پینگ واقعی (اتصال TCP) + گرفتن IP عمومی. */
object Pinger {

    private val ui = Handler(Looper.getMainLooper())

    fun tcpPing(host: String, port: Int, timeoutMs: Int): Double? {
        return try {
            val t0 = System.nanoTime()
            Socket().use { sock ->
                sock.connect(InetSocketAddress(host, port), timeoutMs)
            }
            (System.nanoTime() - t0) / 1_000_000.0
        } catch (_: Exception) {
            null
        }
    }

    /**
     * پینگ موازی همه‌ی سرورها. نتیجه داخل خود Server نوشته می‌شود.
     * onProgress هر ۵ نتیجه روی رشته‌ی UI صدا زده می‌شود.
     */
    fun pingAll(
        servers: List<Server>,
        timeoutMs: Int = 2000,
        workers: Int = 48,
        limit: Int = 150,
        onProgress: (done: Int, total: Int) -> Unit,
        onDone: (alive: Int, tested: Int) -> Unit
    ) {
        val targets = if (limit in 1 until servers.size) servers.take(limit) else servers
        val total = targets.size
        val done = AtomicInteger(0)
        val alive = AtomicInteger(0)
        val pool = Executors.newFixedThreadPool(workers)
        for (s in targets) {
            pool.execute {
                val lat = tcpPing(s.host, s.port, timeoutMs)
                s.latency = lat
                s.alive = lat != null
                if (lat != null) alive.incrementAndGet()
                val d = done.incrementAndGet()
                if (d % 5 == 0 || d == total) {
                    ui.post { onProgress(d, total) }
                }
            }
        }
        pool.shutdown()
        Thread {
            try {
                pool.awaitTermination(180, java.util.concurrent.TimeUnit.SECONDS)
            } catch (_: Exception) {
            }
            ui.post { onDone(alive.get(), total) }
        }.start()
    }

    fun publicIp(timeoutMs: Int = 6000): String? {
        val urls = listOf("https://api.ipify.org", "https://ipinfo.io/ip",
            "https://icanhazip.com")
        for (u in urls) {
            try {
                val conn = (URL(u).openConnection() as HttpURLConnection).apply {
                    connectTimeout = timeoutMs
                    readTimeout = timeoutMs
                    setRequestProperty("User-Agent", "MDavariVPN/2.0")
                }
                if (conn.responseCode == 200) {
                    val t = conn.inputStream.bufferedReader().readText().trim()
                    conn.disconnect()
                    if (t.isNotEmpty() && t.length < 60) return t
                }
            } catch (_: Exception) {
            }
        }
        return null
    }
}
