"""ویجت‌های گرافیکی سفارشی: سپر، نوار پایین، آیکون‌های برداری، نوار پیشرفت."""
from __future__ import annotations

import math
import tkinter as tk

from .theme import Theme


def round_rect(canvas: tk.Canvas, x1, y1, x2, y2, r=14, **kwargs):
    """مستطیل با گوشه‌های گرد روی بوم."""
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)


def draw_icon(canvas: tk.Canvas, name: str, cx: float, cy: float, size: float,
              color: str, tag: str = ""):
    """آیکون‌های برداری ساده (بدون ایموجی تا روی همه‌ی ویندوزها درست بیاید)."""
    s = size
    ids = []
    if name == "sun":
        ids.append(canvas.create_oval(cx - s * .22, cy - s * .22, cx + s * .22, cy + s * .22,
                                      outline=color, width=2, tags=tag))
        for i in range(8):
            a = math.radians(i * 45)
            ids.append(canvas.create_line(
                cx + math.cos(a) * s * .33, cy + math.sin(a) * s * .33,
                cx + math.cos(a) * s * .46, cy + math.sin(a) * s * .46,
                fill=color, width=2, tags=tag))
    elif name == "plane":
        ids.append(canvas.create_polygon(
            cx - s * .45, cy + s * .05, cx + s * .45, cy - s * .38,
            cx + s * .05, cy + s * .45, cx - s * .02, cy + s * .08,
            fill=color, outline="", tags=tag))
    elif name == "gear":
        ids.append(canvas.create_oval(cx - s * .18, cy - s * .18, cx + s * .18, cy + s * .18,
                                      outline=color, width=2, tags=tag))
        for i in range(8):
            a = math.radians(i * 45)
            ids.append(canvas.create_line(
                cx + math.cos(a) * s * .26, cy + math.sin(a) * s * .26,
                cx + math.cos(a) * s * .42, cy + math.sin(a) * s * .42,
                fill=color, width=3, tags=tag))
    elif name == "diamond":
        ids.append(canvas.create_polygon(
            cx, cy - s * .42, cx + s * .42, cy, cx, cy + s * .42, cx - s * .42, cy,
            fill="", outline=color, width=2, tags=tag))
        ids.append(canvas.create_line(cx - s * .42, cy, cx + s * .42, cy,
                                      fill=color, width=1, tags=tag))
        ids.append(canvas.create_line(cx - s * .17, cy - s * .21, cx + s * .17, cy + s * .21,
                                      fill=color, width=1, tags=tag))
        ids.append(canvas.create_line(cx + s * .17, cy - s * .21, cx - s * .17, cy + s * .21,
                                      fill=color, width=1, tags=tag))
    elif name == "home":
        ids.append(canvas.create_polygon(
            cx, cy - s * .40, cx + s * .45, cy + s * .02, cx + s * .32, cy + s * .02,
            cx + s * .32, cy + s * .42, cx - s * .32, cy + s * .42, cx - s * .32, cy + s * .02,
            cx - s * .45, cy + s * .02, fill="", outline=color, width=2, tags=tag))
    elif name == "user":
        ids.append(canvas.create_oval(cx - s * .20, cy - s * .42, cx + s * .20, cy - s * .02,
                                      outline=color, width=2, tags=tag))
        ids.append(canvas.create_arc(cx - s * .40, cy - s * .02, cx + s * .40, cy + s * .78,
                                     start=0, extent=180, style="arc", outline=color,
                                     width=2, tags=tag))
    elif name == "globe":
        ids.append(canvas.create_oval(cx - s * .42, cy - s * .42, cx + s * .42, cy + s * .42,
                                      outline=color, width=2, tags=tag))
        ids.append(canvas.create_line(cx - s * .42, cy, cx + s * .42, cy,
                                      fill=color, width=1, tags=tag))
        ids.append(canvas.create_oval(cx - s * .18, cy - s * .42, cx + s * .18, cy + s * .42,
                                      outline=color, width=1, tags=tag))
    elif name == "crown":
        ids.append(canvas.create_polygon(
            cx - s * .42, cy + s * .28, cx - s * .42, cy - s * .18, cx - s * .20, cy + s * .02,
            cx, cy - s * .34, cx + s * .20, cy + s * .02, cx + s * .42, cy - s * .18,
            cx + s * .42, cy + s * .28, fill=color, outline="", tags=tag))
    elif name == "refresh":
        ids.append(canvas.create_arc(cx - s * .38, cy - s * .38, cx + s * .38, cy + s * .38,
                                     start=40, extent=280, style="arc", outline=color,
                                     width=2, tags=tag))
        ids.append(canvas.create_polygon(
            cx + s * .10, cy - s * .50, cx + s * .50, cy - s * .30, cx + s * .16, cy - s * .10,
            fill=color, outline="", tags=tag))
    elif name == "bolt":
        ids.append(canvas.create_polygon(
            cx - s * .10, cy - s * .45, cx + s * .26, cy - s * .45, cx + s * .02, cy - s * .02,
            cx + s * .22, cy - s * .02, cx - s * .22, cy + s * .48, cx - s * .02, cy + s * .06,
            cx - s * .22, cy + s * .06, fill=color, outline="", tags=tag))
    elif name == "shield":
        ids.append(canvas.create_polygon(
            cx - s * .34, cy - s * .40, cx, cy - s * .52, cx + s * .34, cy - s * .40,
            cx + s * .34, cy + s * .06, cx, cy + s * .50, cx - s * .34, cy + s * .06,
            fill=color, outline="", tags=tag))
    elif name == "back":
        ids.append(canvas.create_line(cx + s * .25, cy - s * .30, cx - s * .20, cy,
                                      cx + s * .25, cy + s * .30, fill=color, width=2,
                                      tags=tag, joinstyle="round"))
    elif name == "copy":
        ids.append(canvas.create_rectangle(cx - s * .32, cy - s * .20, cx + s * .16, cy + s * .36,
                                           outline=color, width=2, tags=tag))
        ids.append(canvas.create_line(cx - s * .10, cy - s * .36, cx + s * .34, cy - s * .36,
                                      cx + s * .34, cy + s * .10, fill=color, width=2, tags=tag))
    return ids


class ShieldButton(tk.Canvas):
    """دکمه‌ی اصلی: سپر با حلقه‌های چرخان (شبیه نمونه)."""

    SIZE = 330

    def __init__(self, parent, theme: Theme, command=None, **kw):
        size = kw.pop("size", self.SIZE)
        bg = theme.c("bg")
        super().__init__(parent, width=size, height=size, bg=bg,
                         highlightthickness=0, bd=0, **kw)
        self.theme = theme
        self.size = size
        self.command = command
        self.state = "idle"
        self.subtitle = "START VPN"
        self.phase = 0.0
        self._pulse = 0.0
        self.bind("<Button-1>", lambda _e: self.command and self.command())
        self.bind("<Enter>", lambda _e: self.configure(cursor="hand2"))
        self.bind("<Leave>", lambda _e: self.configure(cursor=""))
        self.redraw()

    # --- تنظیم وضعیت ---
    def set_state(self, state: str, subtitle: str | None = None):
        self.state = state
        if subtitle is not None:
            self.subtitle = subtitle
        self.redraw()

    def set_subtitle(self, text: str):
        self.subtitle = text
        self.redraw()

    def tick(self):
        """یک فریم انیمیشن."""
        if self.state in ("connecting", "fetching", "pinging"):
            self.phase += 4.0
        elif self.state == "connected":
            self._pulse = (self._pulse + 0.12) % (2 * math.pi)
            self.phase += 0.7
        else:
            self.phase += 0.25
        self.redraw()

    # --- رسم ---
    def redraw(self):
        self.delete("all")
        T = self.theme
        S = self.size
        cx, cy = S / 2, S / 2 - 8

        accent = T.c("accent")
        dim = T.c("accent_dim")
        blue = T.c("blue")
        if self.state == "connected":
            accent = T.c("green")
            dim = T.c("green_dark")
            blue = "#2fa37c"
        elif self.state in ("error",):
            accent = T.c("red")

        # هاله‌ی تدریجی (شبیه‌سازی گلو)
        glows = [("#151d2e", 0.50), ("#111827", 0.44)] if T.mode == "dark" else \
                [("#e3eaf5", 0.50), ("#eaeff8", 0.44)]
        for color, frac in glows:
            r = S * frac
            self.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline="")

        # حلقه‌های چرخان
        ring_specs = [
            (0.470, 120, 12, accent, 6),
            (0.432, 70, 26, blue, 5),
            (0.432, 40, 150, dim, 4),
            (0.396, 150, 20, dim, 4),
        ]
        for frac, extent, offset, color, width in ring_specs:
            r = S * frac
            start = offset + self.phase * (1.0 if width > 4 else -0.6)
            self.create_arc(cx - r, cy - r, cx + r, cy + r, start=start, extent=extent,
                            style="arc", outline=color, width=width)
        if self.state == "connected":
            r = S * (0.47 + 0.02 * math.sin(self._pulse))
            self.create_oval(cx - r, cy - r, cx + r, cy + r, outline=T.c("green"),
                             width=2)

        # سپر دو تکه (شبیه لوگو MD)
        w, h = S * 0.175, S * 0.17
        left = [(cx, cy - h), (cx - w, cy - h * 0.72), (cx - w, cy + h * 0.42),
                (cx, cy + h * 1.05), (cx, cy - h)]
        right = [(cx, cy - h), (cx + w, cy - h * 0.72), (cx + w, cy + h * 0.42),
                 (cx, cy + h * 1.05), (cx, cy - h)]
        self.create_polygon(left, fill="#c8891a", outline=accent, width=2, smooth=False)
        self.create_polygon(right, fill="#8a5f0d", outline=accent, width=2, smooth=False)
        self.create_line(cx, cy - h, cx, cy + h * 1.05, fill=accent, width=1)
        inner = T.c("accent2") if self.state != "connected" else "#5fd39a"
        iw, ih = w * 0.74, h * 0.74
        self.create_polygon(
            cx, cy - ih, cx - iw, cy - ih * 0.70, cx - iw, cy + ih * 0.34,
            cx, cy + ih * 1.02, cx + iw, cy + ih * 0.34, cx + iw, cy - ih * 0.70,
            fill="", outline=inner, width=1)
        self.create_text(cx, cy + h * 0.06, text="MD", fill="#ffffff",
                         font=self.theme.font(int(S * 0.075), bold=True))

        # قرص وضعیت
        pill_w, pill_h = S * 0.42, S * 0.115
        px1, py1 = cx - pill_w / 2, cy + h * 1.55
        px2, py2 = cx + pill_w / 2, py1 + pill_h
        round_rect(self, px1, py1, px2, py2, r=pill_h / 2, fill=T.c("bg2"),
                   outline=accent, width=2)
        self.create_text((px1 + px2) / 2, (py1 + py2) / 2, text=self.subtitle,
                         fill=accent, font=self.theme.font(11, bold=True))


class Pill(tk.Canvas):
    """برچسب قرصی‌شکل برای نمایش IP و پیام‌ها."""

    def __init__(self, parent, theme: Theme, text: str = "", width: int = 420,
                 height: int = 40, color_key: str = "border", **kw):
        super().__init__(parent, width=width, height=height, bg=theme.c("bg"),
                         highlightthickness=0, bd=0, **kw)
        self.theme = theme
        self.color_key = color_key
        self.set_text(text)

    def set_text(self, text: str, color_key: str | None = None):
        self.delete("all")
        if color_key:
            self.color_key = color_key
        T = self.theme
        w = int(self["width"])
        h = int(self["height"])
        round_rect(self, 1, 1, w - 1, h - 1, r=h / 2, fill=T.c("bg2"),
                   outline=T.c(self.color_key), width=1)
        self.create_text(w / 2, h / 2, text=text, fill=T.c("text"),
                         font=T.font(11), anchor="center")


class ProgressBar(tk.Canvas):
    def __init__(self, parent, theme: Theme, width: int = 520, height: int = 10, **kw):
        super().__init__(parent, width=width, height=height, bg=theme.c("bg"),
                         highlightthickness=0, bd=0, **kw)
        self.theme = theme
        self.value = 0.0
        self.bind("<Configure>", lambda _e: self.draw())
        self.draw()

    def set(self, value: float):
        self.value = max(0.0, min(1.0, value))
        self.draw()

    def draw(self):
        self.delete("all")
        T = self.theme
        w = self.winfo_width() or int(self["width"])
        h = self.winfo_height() or int(self["height"])
        round_rect(self, 0, 0, w, h, r=h / 2, fill=T.c("bg2"), outline="")
        if self.value > 0:
            round_rect(self, 0, 0, max(h, w * self.value), h, r=h / 2,
                       fill=T.c("green"), outline="")


class NavBar(tk.Frame):
    """نوار پایین با ۴ دکمه (تنظیمات، خرید، خانه، سرورها)."""

    ITEMS = [("settings", "gear"), ("shop", "diamond"), ("home", "home"),
             ("servers", "user")]

    def __init__(self, parent, theme: Theme, on_select):
        super().__init__(parent, bg=theme.c("bg"))
        self.theme = theme
        self.on_select = on_select
        self.active = "home"
        self.canvas = tk.Canvas(self, height=74, bg=theme.c("bg"),
                                highlightthickness=0, bd=0)
        self.canvas.pack(fill="x")
        self.canvas.bind("<Button-1>", self._click)
        self.canvas.bind("<Configure>", lambda _e: self.draw())

    def set_active(self, name: str):
        self.active = name
        self.draw()

    def _buttons(self):
        try:
            w = self.canvas.winfo_width() or 560
        except Exception:
            w = 560
        n = len(self.ITEMS)
        step = w / n
        out = []
        for i, (name, icon) in enumerate(self.ITEMS):
            cx = step * (i + 0.5)
            out.append((name, icon, cx, w))
        return out

    def _click(self, event):
        for name, _icon, cx, _w in self._buttons():
            if abs(event.x - cx) < 45 and 0 <= event.y <= 80:
                if name != self.active:
                    self.on_select(name)
                return

    def draw(self):
        c = self.canvas
        c.delete("all")
        T = self.theme
        w = c.winfo_width() or 560
        h = 74
        c.configure(bg=T.c("bg"))
        x1, x2 = 18, w - 18
        round_rect(c, x1, 6, x2, h - 8, r=(h - 14) / 2,
                   fill=T.c("card"), outline=T.c("border"), width=1)
        for name, icon, cx, _w in self._buttons():
            if name == self.active:
                round_rect(c, cx - 42, 12, cx + 42, h - 14, r=22,
                           fill=T.c("accent"), outline="")
                color = "#10131a"
            else:
                color = T.c("muted")
            draw_icon(c, icon, cx, h / 2 - 4, 30 if name == "servers" else 26, color)


class IconButton(tk.Canvas):
    """دکمه‌ی آیکونی مربعی گردگوشه (برای هدر)."""

    def __init__(self, parent, theme: Theme, icon: str, command=None,
                 size: int = 44, bg_key: str = "bg2", color_key: str = "text"):
        super().__init__(parent, width=size, height=size, bg=theme.c(bg_key),
                         highlightthickness=0, bd=0)
        self.theme = theme
        self.icon = icon
        self.command = command
        self.size = size
        self.bg_key = bg_key
        self.color_key = color_key
        self.bind("<Button-1>", lambda _e: command and command())
        self.bind("<Enter>", lambda _e: self.configure(cursor="hand2"))
        self.bind("<Leave>", lambda _e: self.configure(cursor=""))
        self.redraw()

    def redraw(self):
        self.delete("all")
        T = self.theme
        s = self.size
        round_rect(self, 1, 1, s - 1, s - 1, r=12, fill=T.c(self.bg_key),
                   outline=T.c("border"), width=1)
        draw_icon(self, self.icon, s / 2, s / 2, s * 0.52, T.c(self.color_key))
