package com.mdavari.vpn.ui

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.util.AttributeSet
import android.view.View

/**
 * دکمه‌ی اصلی برنامه: سپر MD با حلقه‌های چرخان + برچسب وضعیت.
 * وضعیت‌ها: idle / fetching / pinging / connecting / connected / error
 */
class ShieldView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {

    var state: String = "idle"
        set(value) {
            field = value
            invalidate()
        }

    var subtitle: String = "START VPN"
        set(value) {
            field = value
            invalidate()
        }

    private val fill = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.FILL }
    private val stroke = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
    }
    private val text = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        textAlign = Paint.Align.CENTER
        isFakeBoldText = true
    }
    private val shield = Path()
    private val arcRect = RectF()
    private val pillRect = RectF()

    private var phase = 0f
    private var pulse = 0f
    private var frame = 0

    private val ticker = object : Runnable {
        override fun run() {
            frame++
            val fast = state == "connecting" || state == "fetching" || state == "pinging"
            phase += if (fast) 4f else 0.6f
            if (state == "connected") pulse += 0.12f
            invalidate()
            postDelayed(this, if (fast) 16L else 40L)
        }
    }

    init {
        isClickable = true
        setLayerType(LAYER_TYPE_HARDWARE, null)
    }

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        postDelayed(ticker, 40L)
    }

    override fun onDetachedFromWindow() {
        removeCallbacks(ticker)
        super.onDetachedFromWindow()
    }

    private fun dp(v: Float): Float = v * resources.displayMetrics.density

    private fun colors(): Triple<Int, Int, Int> {
        return when (state) {
            "connected" -> Triple(Color.parseColor("#2ECC71"), Color.parseColor("#0F3D24"),
                Color.parseColor("#2FA37C"))
            "error" -> Triple(Color.parseColor("#E74C3C"), Color.parseColor("#3A1512"),
                Color.parseColor("#E74C3C"))
            else -> Triple(Color.parseColor("#F5A623"), Color.parseColor("#6B4A12"),
                Color.parseColor("#3AA0D8"))
        }
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val w = width.toFloat()
        val h = height.toFloat()
        val cx = w / 2f
        val cy = h / 2f - dp(4f)
        val base = minOf(w, h)
        val (accent, dim, blue) = colors()

        // هاله
        fill.color = Color.parseColor("#131C2E")
        canvas.drawCircle(cx, cy, base * 0.47f, fill)
        fill.color = Color.parseColor("#0F1725")
        canvas.drawCircle(cx, cy, base * 0.41f, fill)

        // حلقه‌های چرخان
        drawRing(canvas, cx, cy, base * 0.470f, 120f, 12f + phase, accent, dp(6f))
        drawRing(canvas, cx, cy, base * 0.432f, 70f, 26f + phase, blue, dp(5f))
        drawRing(canvas, cx, cy, base * 0.432f, 40f, 150f - phase * 0.6f, dim, dp(4f))
        drawRing(canvas, cx, cy, base * 0.396f, 150f, 20f - phase * 0.6f, dim, dp(4f))
        if (state == "connected") {
            stroke.color = accent
            stroke.strokeWidth = dp(2f)
            stroke.alpha = (140 + 80 * kotlin.math.sin(pulse)).toInt().coerceIn(60, 220)
            canvas.drawCircle(cx, cy, base * (0.468f + 0.012f * kotlin.math.sin(pulse)), stroke)
            stroke.alpha = 255
        }

        // سپر
        val sw = base * 0.175f
        val sh = base * 0.170f
        shield.reset()
        shield.moveTo(cx, cy - sh)
        shield.lineTo(cx + sw, cy - sh * 0.72f)
        shield.lineTo(cx + sw, cy + sh * 0.42f)
        shield.lineTo(cx, cy + sh * 1.05f)
        shield.lineTo(cx - sw, cy + sh * 0.42f)
        shield.lineTo(cx - sw, cy - sh * 0.72f)
        shield.close()

        fill.color = if (state == "connected") Color.parseColor("#1E7A50") else Color.parseColor("#8A5F0D")
        canvas.drawPath(shield, fill)
        fill.color = if (state == "connected") Color.parseColor("#2ECC71") else Color.parseColor("#F5A623")
        fill.alpha = 90
        canvas.drawPath(shield, fill)
        fill.alpha = 255

        stroke.color = accent
        stroke.strokeWidth = dp(2f)
        canvas.drawPath(shield, stroke)

        text.color = Color.WHITE
        text.textSize = base * 0.072f
        canvas.drawText("MD", cx, cy + base * 0.026f, text)

        // قرص وضعیت
        val pillW = base * 0.44f
        val pillH = dp(34f)
        pillRect.set(cx - pillW / 2f, cy + sh * 1.5f, cx + pillW / 2f, cy + sh * 1.5f + pillH)
        fill.color = Color.parseColor("#141C2B")
        canvas.drawRoundRect(pillRect, pillH / 2f, pillH / 2f, fill)
        stroke.color = accent
        stroke.strokeWidth = dp(2f)
        canvas.drawRoundRect(pillRect, pillH / 2f, pillH / 2f, stroke)
        text.color = accent
        text.textSize = dp(13f)
        canvas.drawText(subtitle, cx, pillRect.centerY() + dp(5f), text)
    }

    private fun drawRing(canvas: Canvas, cx: Float, cy: Float, r: Float,
                         extent: Float, start: Float, color: Int, width: Float) {
        arcRect.set(cx - r, cy - r, cx + r, cy + r)
        stroke.color = color
        stroke.strokeWidth = width
        canvas.drawArc(arcRect, start, extent, false, stroke)
    }
}
