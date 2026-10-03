package com.mdavari.vpn

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.CheckBox
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.ListView
import android.widget.ProgressBar
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.mdavari.vpn.model.Server
import com.mdavari.vpn.net.Pinger
import com.mdavari.vpn.net.Sources
import com.mdavari.vpn.ui.ServerAdapter
import com.mdavari.vpn.ui.ShieldView
import com.mdavari.vpn.util.Fmt
import com.mdavari.vpn.util.Prefs
import com.mdavari.vpn.vpn.ProfileBridge

/**
 * MDavari VPN PRO — اندروید (فاز A: اپ کمکی هوشمند)
 * لیست/پینگ/انتخاب سریع‌ترین سرور + ساخت پروفایل و پاس دادن به اپ OpenVPN.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var prefs: Prefs
    private lateinit var adapter: ServerAdapter
    private val ui = Handler(Looper.getMainLooper())

    private var servers: List<Server> = emptyList()
    private var configs: Map<String, String> = emptyMap()
    private var state = "idle"
    private var candidate: Server? = null       // سروری که پروفایلش باز شده
    private var connectedServer: Server? = null
    private var connectedAt = 0L
    private var publicIp: String? = null
    private var fetching = false
    private var pinging = false
    private var lastIpCheck = 0L

    private lateinit var pages: Map<String, View>
    private lateinit var shield: ShieldView
    private lateinit var txtStatusTitle: TextView
    private lateinit var txtStatusSub: TextView
    private lateinit var txtIpPill: TextView
    private lateinit var txtCardTitle: TextView
    private lateinit var txtCardValue: TextView
    private lateinit var txtInfoServer: TextView
    private lateinit var txtInfoCountry: TextView
    private lateinit var txtInfoPing: TextView
    private lateinit var txtInfoUptime: TextView
    private lateinit var listServers: ListView
    private lateinit var spCountry: Spinner
    private lateinit var chkOnlyAlive: CheckBox
    private lateinit var txtStats: TextView
    private lateinit var progress: ProgressBar
    private lateinit var txtLog: TextView
    private lateinit var navIcons: Map<String, ImageView>
    private lateinit var navHomeBg: View

    private val logLines = ArrayDeque<String>()

    // ------------------------------------------------------------------
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        prefs = Prefs(this)
        adapter = ServerAdapter(this)

        bindViews()
        forceRtl()
        setupNav()
        setupServersPage()
        setupSettingsPage()
        setupShopPage()
        setupHomeActions()

        // لیست ذخیره‌شده را فوراً نشان بده
        val (cachedServers, cachedConfigs) = Sources.loadCache(this)
        if (cachedServers.isNotEmpty()) {
            servers = cachedServers
            configs = cachedConfigs
            adapter.setData(servers)
            log("~ ${servers.size} سرور از حافظه‌ی قبلی بارگذاری شد")
        }
        updateStats()
        refreshList(autoPing = prefs.autoPingAfterFetch)

        ui.postDelayed(ticker, 1000)
    }

    private fun bindViews() {
        pages = mapOf(
            "home" to findViewById(R.id.pageHome),
            "servers" to findViewById(R.id.pageServers),
            "shop" to findViewById(R.id.pageShop),
            "settings" to findViewById(R.id.pageSettings)
        )
        shield = findViewById(R.id.shieldView)
        txtStatusTitle = findViewById(R.id.txtStatusTitle)
        txtStatusSub = findViewById(R.id.txtStatusSub)
        txtIpPill = findViewById(R.id.txtIpPill)
        txtCardTitle = findViewById(R.id.txtCardTitle)
        txtCardValue = findViewById(R.id.txtCardValue)
        txtInfoServer = findViewById(R.id.txtInfoServer)
        txtInfoCountry = findViewById(R.id.txtInfoCountry)
        txtInfoPing = findViewById(R.id.txtInfoPing)
        txtInfoUptime = findViewById(R.id.txtInfoUptime)
        listServers = findViewById(R.id.listServers)
        spCountry = findViewById(R.id.spCountry)
        chkOnlyAlive = findViewById(R.id.chkOnlyAlive)
        txtStats = findViewById(R.id.txtStats)
        progress = findViewById(R.id.progress)
        txtLog = findViewById(R.id.txtLog)
        navHomeBg = findViewById(R.id.navHomeBg)
        navIcons = mapOf(
            "home" to findViewById(R.id.iconNavHome),
            "servers" to findViewById(R.id.iconNavServers),
            "shop" to findViewById(R.id.iconNavShop),
            "settings" to findViewById(R.id.iconNavSettings)
        )
    }

    private fun forceRtl() {
        val dir = View.LAYOUT_DIRECTION_RTL
        pages.values.forEach { it.layoutDirection = dir }
        findViewById<View>(R.id.pageContainer).layoutDirection = dir
    }

    // ------------------------------------------------------------------
    // ناوبری
    // ------------------------------------------------------------------
    private fun setupNav() {
        findViewById<View>(R.id.navHome).setOnClickListener { showPage("home") }
        findViewById<View>(R.id.navServers).setOnClickListener { showPage("servers") }
        findViewById<View>(R.id.navShop).setOnClickListener { showPage("shop") }
        findViewById<View>(R.id.navSettings).setOnClickListener { showPage("settings") }
        showPage("home")
    }

    private fun showPage(name: String) {
        for ((key, view) in pages) {
            view.visibility = if (key == name) View.VISIBLE else View.GONE
        }
        val active = Color.parseColor("#F5A623")
        val idle = Color.parseColor("#8C9AB4")
        navIcons.forEach { (key, icon) ->
            icon.setColorFilter(if (key == name) active else idle)
        }
        navHomeBg.visibility = if (name == "home") View.VISIBLE else View.INVISIBLE
    }

    override fun onBackPressed() {
        if (pages["home"]?.visibility != View.VISIBLE) showPage("home") else super.onBackPressed()
    }

    // ------------------------------------------------------------------
    // صفحه‌ی خانه
    // ------------------------------------------------------------------
    private fun setupHomeActions() {
        shield.setOnClickListener { onMainButton() }
        findViewById<View>(R.id.cardSmart).setOnClickListener { showPage("servers") }
        findViewById<View>(R.id.btnCardBack).setOnClickListener { showPage("servers") }
        findViewById<View>(R.id.btnHeaderRefresh).setOnClickListener { refreshList(true) }
        findViewById<View>(R.id.btnNewList).setOnClickListener { refreshList(true) }
        findViewById<View>(R.id.btnPingQuick).setOnClickListener { startPing() }
        findViewById<View>(R.id.btnSwitchIp).setOnClickListener { switchIp() }
        findViewById<ImageButton>(R.id.btnTelegram).setOnClickListener { openTelegram() }
    }

    private fun onMainButton() {
        if (state == "fetching" || state == "pinging") {
            toast("لطفاً تا پایان عملیات جاری صبر کن"); return
        }
        if (state == "connected") {
            val pkg = ProfileBridge.installedClient(this)
            if (pkg != null) {
                try {
                    startActivity(packageManager.getLaunchIntentForPackage(pkg))
                } catch (_: Exception) {
                }
                toast("برای قطع، در اپ OpenVPN دکمه‌ی قطع را بزن")
            } else {
                toast("برای قطع اتصال، از تنظیمات اندروید → VPN اقدام کن")
            }
            return
        }
        if (servers.isEmpty()) { refreshList(true); return }
        connectBest()
    }

    private fun setState(newState: String, subtitle: String? = null) {
        state = newState
        val sub = subtitle ?: when (newState) {
            "fetching" -> "FETCHING"
            "pinging" -> "TESTING"
            "connecting" -> "CONNECTING"
            "connected" -> "PROTECTED"
            else -> "START VPN"
        }
        shield.state = newState
        shield.subtitle = sub
        when (newState) {
            "connected" -> {
                txtStatusTitle.text = getString(R.string.protected_title)
                txtStatusTitle.setTextColor(Color.parseColor("#2ECC71"))
                txtStatusSub.text = getString(R.string.protected_sub)
            }
            "fetching" -> {
                txtStatusTitle.text = "در حال دریافت لیست سرورها…"
                txtStatusTitle.setTextColor(Color.parseColor("#F5A623"))
                txtStatusSub.text = "چند لحظه صبر کن"
            }
            "pinging" -> {
                txtStatusTitle.text = "تست پینگ سرورها…"
                txtStatusTitle.setTextColor(Color.parseColor("#F5A623"))
                txtStatusSub.text = "پینگ واقعی همه‌ی سرورها گرفته می‌شود"
            }
            "connecting" -> {
                txtStatusTitle.text = "در حال اتصال…"
                txtStatusTitle.setTextColor(Color.parseColor("#F5A623"))
                txtStatusSub.text = candidate?.label ?: "پروفایل آماده شد"
            }
            else -> {
                txtStatusTitle.text = getString(R.string.ready_title)
                txtStatusTitle.setTextColor(Color.parseColor("#E9EEF8"))
                txtStatusSub.text = getString(R.string.ready_sub)
            }
        }
        updateHomeCard()
    }

    private fun updateHomeCard() {
        val srv = connectedServer
        if (srv != null) {
            txtCardTitle.text = "سرور متصل کنونی"
            txtCardTitle.setTextColor(Color.parseColor("#2ECC71"))
            val secs = if (connectedAt > 0) (System.currentTimeMillis() - connectedAt) / 1000 else 0
            txtCardValue.text = "متصل به: ${srv.label} • مدت ${Fmt.fa(secs)} ثانیه"
            txtInfoServer.text = srv.label
            txtInfoCountry.text = srv.countryFa
            txtInfoPing.text = srv.pingText
            txtInfoUptime.text = Fmt.clock(secs)
        } else {
            txtCardTitle.text = "سرورهای هوشمند"
            txtCardTitle.setTextColor(Color.parseColor("#E9EEF8"))
            val alive = servers.count { it.alive == true }
            txtCardValue.text = "اتصال خودکار • ${Fmt.fa(servers.size)} سرور • " +
                    "${Fmt.fa(alive)} فعال"
            txtInfoServer.text = "—"
            txtInfoCountry.text = "—"
            txtInfoPing.text = "—"
            txtInfoUptime.text = "—"
        }
    }

    // ------------------------------------------------------------------
    // صفحه‌ی سرورها
    // ------------------------------------------------------------------
    private fun setupServersPage() {
        listServers.adapter = adapter
        listServers.setOnItemClickListener { _: AdapterView<*>?, _: View?, position: Int, _: Long ->
            val s = adapter.getItem(position) as Server
            connectTo(s)
        }
        chkOnlyAlive.setOnCheckedChangeListener { _, checked ->
            adapter.setOnlyAlive(checked)
            updateStats()
        }
        spCountry.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                val label = parent?.getItemAtPosition(position)?.toString()
                adapter.setCountry(if (position == 0) null else label)
                updateStats()
            }

            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }
        findViewById<Button>(R.id.btnConnectBest).setOnClickListener { connectBest() }
        findViewById<Button>(R.id.btnRefreshList).setOnClickListener { refreshList(true) }
        findViewById<Button>(R.id.btnPingReal).setOnClickListener { startPing() }
    }

    private fun refreshCountrySpinner() {
        val items = ArrayList<String>()
        items.add(getString(R.string.all_countries) + " (All Countries)")
        items.addAll(adapter.countries())
        val aa = ArrayAdapter(this, android.R.layout.simple_spinner_item, items)
        aa.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        spCountry.adapter = aa
    }

    private fun updateStats() {
        val tested = servers.count { it.alive != null || it.latency != null }
        val alive = servers.count { it.alive == true }
        txtStats.text = "کل: ${Fmt.fa(servers.size)} • تست‌شده: ${Fmt.fa(tested)} • فعال: ${Fmt.fa(alive)}"
        if (state != "pinging") {
            progress.progress = if (servers.isEmpty()) 0 else (alive * 100 / servers.size)
        }
    }

    // ------------------------------------------------------------------
    // گرفتن لیست و پینگ
    // ------------------------------------------------------------------
    private fun refreshList(autoPing: Boolean) {
        if (fetching) return
        fetching = true
        setState("fetching")
        log("… شروع دریافت لیست سرورها")
        Thread {
            val result = try {
                Sources.refresh(this) { line -> ui.post { log(line) } }
            } catch (e: Exception) {
                ui.post { log("✗ خطای دریافت لیست: ${e.message}") }
                Sources.Result(emptyList<Server>(), emptyMap<String, String>(), "error")
            }
            ui.post {
                fetching = false
                if (result.servers.isNotEmpty()) {
                    servers = result.servers.let { list ->
                        if (prefs.onlyPort443) list.filter { s -> s.port == 443 } else list
                    }
                    if (result.ovpnConfigs.isNotEmpty()) configs = result.ovpnConfigs
                    adapter.setData(servers)
                    refreshCountrySpinner()
                    updateStats()
                    setState("idle")
                    log("✓ لیست آماده شد: ${servers.size} سرور (منابع: ${result.report})")
                    if (autoPing) startPing()
                } else {
                    setState("idle")
                    toast("لیست سرورها دریافت نشد؛ اینترنت را بررسی کن")
                }
            }
        }.start()
    }

    private fun startPing() {
        if (servers.isEmpty()) {
            toast("اول لیست سرورها را دریافت کن"); return
        }
        if (pinging) return
        pinging = true
        setState("pinging")
        val timeout = prefs.pingTimeout * 1000
        log("> تست پینگ واقعی روی ${servers.size} سرور …")
        Pinger.pingAll(
            servers = servers,
            timeoutMs = timeout,
            workers = 48,
            limit = 150,
            onProgress = { done, total ->
                progress.progress = done * 100 / maxOf(1, total)
                val alive = servers.count { it.alive == true }
                txtStats.text = "کل: ${Fmt.fa(servers.size)} • تست‌شده: ${Fmt.fa(done)}/${Fmt.fa(total)} • فعال: ${Fmt.fa(alive)}"
            },
            onDone = { alive, tested ->
                pinging = false
                log("✓ ${alive} سرور فعال از ${tested} سرور تست‌شده")
                adapter.notifyDataSetChanged()
                updateStats()
                setState("idle")
            }
        )
    }

    // ------------------------------------------------------------------
    // اتصال
    // ------------------------------------------------------------------
    private fun bestServers(exclude: Set<String>): List<Server> {
        val pool = servers.filter { it.port == 443 && it.key !in exclude }
        val alive = pool.filter { it.alive == true }
        return (if (alive.isNotEmpty()) alive else pool).sortedBy { it.latency ?: 9e9 }
    }

    private fun connectBest() {
        val pool = bestServers(setOfNotNull(connectedServer?.key))
        if (pool.isEmpty()) {
            toast("سرور مناسبی پیدا نشد؛ لیست جدید بگیر")
            return
        }
        connectTo(pool.first())
    }

    private fun switchIp() {
        if (servers.isEmpty()) { toast("اول لیست بگیر"); return }
        val current = connectedServer?.key
        val pool = bestServers(setOfNotNull(current))
        if (pool.isEmpty()) { toast("سرور دیگری برای تغییر IP نیست"); return }
        log("… تغییر IP → ${pool.first().label}")
        connectTo(pool.first())
    }

    private fun connectTo(server: Server) {
        if (prefs.l2tpPreferred) {
            showL2tpDialog(server)
            return
        }
        val cfg = configs[server.host]
        if (cfg != null) {
            openProfile(server, cfg)
            return
        }
        AlertDialog.Builder(this)
            .setTitle("انتخاب روش اتصال")
            .setMessage("برای این سرور کانفیگ OpenVPN نداریم.\n\n" +
                    "می‌توانی همین حالا کانفیگ را از منبع رسمی بگیریم، " +
                    "یا با L2TP/IPSec داخلی اندروید وصل شوی.")
            .setPositiveButton("گرفتن کانفیگ OpenVPN") { _, _ -> fetchConfigThen(server) }
            .setNeutralButton("راهنمای L2TP") { _, _ -> showL2tpDialog(server) }
            .setNegativeButton("بستن", null)
            .show()
    }

    private fun fetchConfigThen(server: Server) {
        toast("در حال گرفتن کانفیگ…")
        Thread {
            try {
                val (_, cfg) = Sources.refresh(this) { line -> ui.post { log(line) } }
                ui.post {
                    if (cfg.isNotEmpty()) configs = cfg
                    val found = cfg[server.host]
                    if (found != null) openProfile(server, found)
                    else {
                        log("! کانفیگ این سرور در منبع رسمی نبود → راهنمای L2TP")
                        showL2tpDialog(server)
                    }
                }
            } catch (e: Exception) {
                ui.post {
                    log("✗ گرفتن کانفیگ ناموفق: ${e.message}")
                    showL2tpDialog(server)
                }
            }
        }.start()
    }

    private fun openProfile(server: Server, ovpn: String) {
        val uri: Uri? = ProfileBridge.writeProfile(this, server, ovpn)
        if (uri == null) {
            toast("ساخت فایل پروفایل ناموفق بود")
            return
        }
        candidate = server
        setState("connecting", server.label)
        val installed = ProfileBridge.installedClient(this)
        if (!installed) {
            log("! اپ OpenVPN روی گوشی نصب نیست")
            AlertDialog.Builder(this)
                .setTitle("اپ OpenVPN نصب نیست")
                .setMessage("پروفایل ساخته شد، ولی برای اتصال به یک کلاینت OpenVPN نیاز است.\n" +
                        "OpenVPN for Android را نصب کن (رایگان و اپن‌سورس) و بعد دوباره دکمه‌ی اتصال را بزن.\n\n" +
                        "اگر نمی‌خواهی اپ نصب کنی، می‌توانی از L2TP/IPSec داخلی اندروید استفاده کنی.")
                .setPositiveButton("نصب اپ OpenVPN") { _, _ ->
                    ProfileBridge.openStorePage(this, ProfileBridge.OPENVPN_FOR_ANDROID)
                }
                .setNeutralButton("راهنمای L2TP") { _, _ -> showL2tpDialog(server) }
                .setNegativeButton("بستن", null)
                .show()
            setState("idle")
            return
        }
        if (!prefs.autoOpenClient) {
            log("✓ پروفایل ساخته شد: ${server.label} (باز کردن خودکار خاموش است)")
            toast("پروفایل ساخته شد؛ از تنظیمات، باز شدن خودکار را روشن کن یا دستی باز کن")
            setState("idle")
            return
        }
        val opened = ProfileBridge.openInClient(this, uri)
        if (opened) {
            log("✓ پروفایل ${server.label} به اپ OpenVPN فرستاده شد")
            log("i در اپ OpenVPN دکمه‌ی اتصال را بزن (یا اتصال خودکار را فعال کن)")
            toast("در اپ OpenVPN دکمه‌ی اتصال را بزن")
        } else {
            log("! باز کردن اپ OpenVPN ناموفق بود")
            toast("باز کردن اپ OpenVPN ناموفق بود")
            setState("idle")
        }
    }

    private fun showL2tpDialog(server: Server) {
        val guide = ProfileBridge.l2tpGuide(server)
        AlertDialog.Builder(this)
            .setTitle("اتصال با L2TP/IPSec (داخلی اندروید)")
            .setMessage(guide)
            .setPositiveButton("کپی راهنما") { _, _ ->
                copyToClipboard(server.label)
                toast("آدرس سرور کپی شد")
            }
            .setNeutralButton("بستن", null)
            .show()
    }

    // ------------------------------------------------------------------
    // تنظیمات و خرید
    // ------------------------------------------------------------------
    private fun setupSettingsPage() {
        val timeouts = listOf("۱ ثانیه", "۲ ثانیه", "۳ ثانیه", "۵ ثانیه")
        val aa = ArrayAdapter(this, android.R.layout.simple_spinner_item, timeouts)
        aa.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        spTimeout.adapter = aa
        val values = listOf(1, 2, 3, 5)
        val idx = values.indexOf(prefs.pingTimeout).coerceAtLeast(0)
        spTimeout.setSelection(idx)
        spTimeout.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                prefs.pingTimeout = values[position]
                log("# تنظیم تایم‌اوت = ${values[position]} ثانیه")
            }

            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }

        bindCheck(R.id.chkPort443, prefs.onlyPort443) { prefs.onlyPort443 = it; log("# فقط پورت ۴۴۳ = $it") }
        bindCheck(R.id.chkAutoReconnect, prefs.autoReconnect) { prefs.autoReconnect = it }
        bindCheck(R.id.chkPingAfterFetch, prefs.autoPingAfterFetch) { prefs.autoPingAfterFetch = it }
        bindCheck(R.id.chkAutoOpen, prefs.autoOpenClient) { prefs.autoOpenClient = it }
        bindCheck(R.id.chkL2tpHint, prefs.l2tpPreferred) { prefs.l2tpPreferred = it }

        findViewById<Button>(R.id.btnClearCache).setOnClickListener {
            try {
                java.io.File(filesDir, "servers_cache.json").delete()
                java.io.File(filesDir, "ovpn_cache.json").delete()
                log("# کش پاک شد")
                toast("کش پاک شد")
            } catch (e: Exception) {
                log("! پاک کردن کش ناموفق: ${e.message}")
            }
        }
        findViewById<Button>(R.id.btnVersion).setOnClickListener {
            toast("MDavari VPN v${BuildConfig.VERSION_NAME} — اندروید")
        }
    }

    private fun bindCheck(id: Int, initial: Boolean, onChange: (Boolean) -> Unit) {
        val chk = findViewById<CheckBox>(id)
        chk.isChecked = initial
        chk.setOnCheckedChangeListener { _, checked -> onChange(checked) }
    }

    private fun setupShopPage() {
        findViewById<TextView>(R.id.txtDeviceId).text = "کد یکتای دستگاه: ${prefs.deviceId}"
        findViewById<Button>(R.id.btnCopyWallet).setOnClickListener {
            copyToClipboard(ProfileBridge.WALLET_TRC20)
            toast("آدرس کیف پول کپی شد")
        }
        findViewById<Button>(R.id.btnSendReceipt).setOnClickListener { openTelegram() }
        findViewById<Button>(R.id.btnSupport).setOnClickListener { openTelegram() }
        findViewById<Button>(R.id.btnChangeKey).setOnClickListener {
            toast("کد دستگاه: ${prefs.deviceId}")
        }

        val row: android.widget.LinearLayout = findViewById(R.id.rowPlans1)
        val plans = listOf(
            Triple("اقتصادی — ۱ ماهه", "۳۰ روز نامحدود", "۲ تراکنش"),
            Triple("پرفروش — ۳ ماهه", "۹۰ روز نامحدود", "۵ تراکنش"),
            Triple("پیشنهاد ویژه — ۶ ماهه", "۱۸۰ روز نامحدود", "۸ تراکنش"),
            Triple("یکساله طلایی", "۳۶۵ روز نامحدود", "۱۲ تراکنش")
        )
        val lp = android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
        for (p in plans) {
            val box = android.widget.LinearLayout(this).apply {
                orientation = android.widget.LinearLayout.VERTICAL
                setBackgroundResource(R.drawable.bg_card)
                setPadding(20, 20, 20, 20)
            }
            box.addView(TextView(this).apply {
                text = p.first
                setTextColor(Color.parseColor("#F5A623"))
                textSize = 13f
                textAlignment = View.TEXT_ALIGNMENT_CENTER
            })
            box.addView(TextView(this).apply {
                text = p.second
                setTextColor(Color.parseColor("#E9EEF8"))
                textSize = 12f
                textAlignment = View.TEXT_ALIGNMENT_CENTER
                setPadding(0, 8, 0, 0)
            })
            box.addView(TextView(this).apply {
                text = "قیمت: ${p.third}"
                setTextColor(Color.parseColor("#8C9AB4"))
                textSize = 11f
                textAlignment = View.TEXT_ALIGNMENT_CENTER
                setPadding(0, 8, 0, 0)
            })
            box.layoutParams = android.widget.LinearLayout.LayoutParams(lp).apply {
                marginEnd = 12
            }
            row.addView(box)
        }
    }

    // ------------------------------------------------------------------
    // ابزارها
    // ------------------------------------------------------------------
    private fun openTelegram() {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(ProfileBridge.TELEGRAM_URL)))
        } catch (_: Exception) {
            toast("باز کردن تلگرام ناموفق بود")
        }
    }

    private fun copyToClipboard(text: String) {
        try {
            val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            cm.setPrimaryClip(ClipData.newPlainText("MDavariVPN", text))
        } catch (_: Exception) {
        }
    }

    private fun toast(text: String) {
        Toast.makeText(this, text, Toast.LENGTH_SHORT).show()
    }

    private fun log(line: String) {
        logLines.addLast("[${Fmt.now()}] $line")
        while (logLines.size > 300) logLines.removeFirst()
        txtLog.text = logLines.joinToString("\n")
        txtLog.post {
            try {
                val amount = txtLog.lineCount * txtLog.lineHeight
                if (amount > txtLog.height) txtLog.scrollTo(0, amount - txtLog.height)
            } catch (_: Exception) {
            }
        }
    }

    private fun refreshIp() {
        Thread {
            val ip = Pinger.publicIp()
            ip?.let { value -> ui.post { publicIp = value } }
        }.start()
    }

    // ------------------------------------------------------------------
    // حلقه‌ی وضعیت
    // ------------------------------------------------------------------
    private val ticker = object : Runnable {
        override fun run() {
            val active = ProfileBridge.vpnActive(this@MainActivity)
            if (active && state != "connected") {
                state = "connected"
                connectedAt = System.currentTimeMillis()
                connectedServer = candidate
                if (connectedServer != null) adapter.connectedKey = connectedServer!!.key
                setState("connected")
                log("✓ تونل VPN فعال شد")
                refreshIp()
                lastIpCheck = System.currentTimeMillis()
            } else if (!active && state == "connected") {
                log("! اتصال VPN قطع شد")
                connectedServer = null
                adapter.connectedKey = null
                connectedAt = 0
                setState("idle")
                if (prefs.autoReconnect) {
                    log("… تلاش برای اتصال مجدد")
                    connectBest()
                }
            }

            if (state == "connected") {
                val secs = (System.currentTimeMillis() - connectedAt) / 1000
                txtIpPill.background = getDrawable(R.drawable.bg_pill_green)
                txtIpPill.text = "IP: ${publicIp ?: "—"}   •   ${Fmt.clock(secs)}"
                txtIpPill.setTextColor(Color.parseColor("#2ECC71"))
                if (System.currentTimeMillis() - lastIpCheck > 25000) {
                    lastIpCheck = System.currentTimeMillis()
                    refreshIp()
                }
            } else {
                txtIpPill.background = getDrawable(R.drawable.bg_pill)
                txtIpPill.setTextColor(Color.parseColor("#E9EEF8"))
                txtIpPill.text = if (publicIp != null) "آی‌پی فعلی: $publicIp" else "آی‌پی فعلی: —"
            }
            updateHomeCard()
            ui.postDelayed(this, 1000)
        }
    }

    override fun onDestroy() {
        ui.removeCallbacksAndMessages(null)
        super.onDestroy()
    }
}
