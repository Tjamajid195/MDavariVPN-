package com.mdavari.vpn.vpn

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.Uri
import androidx.core.content.FileProvider
import android.os.Build
import com.mdavari.vpn.model.Server
import java.io.File

/**
 * پل ارتباطی به اپ‌های VPN اندروید.
 *
 * اندروید SSTP داخلی ندارد؛ پس در این فاز:
 *  ۱) پروفایل OpenVPN همان سرور ساخته و به اپ «OpenVPN for Android» پاس داده می‌شود
 *     (یک لمس برای اتصال؛ یا با تیک «اتصال خودکار» در خود آن اپ).
 *  ۲) اگر کانفیگ OpenVPN موجود نباشد، راهنمای L2TP/IPSec با vpn/vpn نمایش داده می‌شود.
 */
object ProfileBridge {

    const val OPENVPN_FOR_ANDROID = "de.blinkt.openvpn"
    const val OPENVPN_CONNECT = "net.openvpn.openvpn"
    const val MIME_OVPN = "application/x-openvpn-profile"
    const val TELEGRAM_URL = "https://t.me/"
    const val WALLET_TRC20 = "TZ6XSBGTEAfwKw4KGNDPcNQBHBSe5pEX6A"

    fun profileDir(ctx: Context): File {
        val dir = File(ctx.filesDir, "profiles")
        if (!dir.exists()) dir.mkdirs()
        return dir
    }

    /** فایل .ovpn را می‌نویسد و Uri قابل اشتراک برمی‌گرداند. */
    fun writeProfile(ctx: Context, server: Server, ovpn: String): Uri? {
        return try {
            val safeHost = server.host.replace(Regex("[^A-Za-z0-9.\\-]"), "_")
            val f = File(profileDir(ctx), "mdavari-$safeHost.ovpn")
            f.writeText(ovpn, Charsets.UTF_8)
            FileProvider.getUriForFile(ctx, "${ctx.packageName}.fileprovider", f)
        } catch (_: Exception) {
            null
        }
    }

    fun isInstalled(ctx: Context, pkg: String): Boolean {
        return try {
            ctx.packageManager.getPackageInfo(pkg, 0)
            true
        } catch (_: Exception) {
            false
        }
    }

    fun installedClient(ctx: Context): String? {
        if (isInstalled(ctx, OPENVPN_FOR_ANDROID)) return OPENVPN_FOR_ANDROID
        if (isInstalled(ctx, OPENVPN_CONNECT)) return OPENVPN_CONNECT
        return null
    }

    /**
     * تلاش برای باز کردن پروفایل در اپ OpenVPN (نصب‌شده یا با انتخابگر اندروید).
     * true = Intent باز شد.
     */
    fun openInClient(activity: Activity, uri: Uri): Boolean {
        val pkg = installedClient(activity)
        val base = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, MIME_OVPN)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        if (pkg != null) {
            try {
                activity.startActivity(Intent(base).setPackage(pkg))
                return true
            } catch (_: Exception) {
            }
        }
        return try {
            val chooser = Intent.createChooser(base, "انتخاب اپ OpenVPN")
            activity.startActivity(chooser)
            true
        } catch (_: Exception) {
            false
        }
    }

    /** مسیر فایل پروفایل (برای نمایش/اشتراک دستی). */
    fun profileList(ctx: Context): List<File> = profileDir(ctx).listFiles()?.toList() ?: emptyList()

    fun openStorePage(ctx: Context, pkg: String) {
        try {
            ctx.startActivity(Intent(Intent.ACTION_VIEW,
                Uri.parse("market://details?id=$pkg")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        } catch (_: Exception) {
            try {
                ctx.startActivity(Intent(Intent.ACTION_VIEW,
                    Uri.parse("https://play.google.com/store/apps/details?id=$pkg"))
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            } catch (_: Exception) {
            }
        }
    }

    /** متن راهنمای L2TP/IPSec برای هر سرور. */
    fun l2tpGuide(server: Server): String {
        return buildString {
            appendLine("راه‌های اتصال به این سرور روی اندروید")
            appendLine()
            appendLine("۱) راه پیشنهادی (OpenVPN):")
            appendLine("   دکمه‌ی «اتصال» را بزن؛ پروفایل ساخته می‌شود و در اپ OpenVPN باز می‌شود.")
            appendLine()
            appendLine("۲) راه دومی (L2TP/IPSec داخلی اندروید):")
            appendLine("   تنظیمات → شبکه و اینترنت → VPN → افزودن VPN")
            appendLine("   نوع: L2TP/IPSec PSK")
            appendLine("   سرور: ${server.label}")
            appendLine("   کلید PSK: vpn")
            appendLine("   نام کاربری: vpn")
            appendLine("   رمز عبور: vpn")
            appendLine()
            appendLine("توجه: سرورهای رایگان ممکن است فقط یکی از این دو راه را پشتیبانی کنند؛")
            appendLine("اگر یکی وصل نشد سرور دیگری را امتحان کن.")
        }
    }

    /** آیا در حال حاضر تونل VPN روی دستگاه فعال است؟ */
    fun vpnActive(ctx: Context): Boolean {
        return try {
            val cm = ctx.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
            val net = cm.activeNetwork ?: return false
            val caps = cm.getNetworkCapabilities(net) ?: return false
            caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN)
        } catch (_: Exception) {
            false
        }
    }
}
