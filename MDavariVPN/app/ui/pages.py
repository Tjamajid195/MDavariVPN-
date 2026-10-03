"""ساخت صفحات برنامه (خانه، سرورها، خرید، تنظیمات)."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .. import config
from ..sources import COUNTRY_FA
from .theme import Theme
from .widgets import IconButton, Pill, ProgressBar, ShieldButton, draw_icon, round_rect


# ---------------------------------------------------------------------------
# ابزارهای مشترک
# ---------------------------------------------------------------------------
def label(parent, theme: Theme, text: str = "", size: int = 11, bold: bool = False,
          color: str = "text", wrap: int | None = None, anchor: str = "e", **kw):
    lbl = tk.Label(parent, text=text, bg=parent["bg"], fg=theme.c(color),
                   font=theme.font(size, bold), anchor=anchor, justify="right", **kw)
    if wrap:
        lbl.configure(wraplength=wrap)
    return lbl


def card(parent, theme: Theme, pad: int = 12) -> tk.Frame:
    frame = tk.Frame(parent, bg=theme.c("card"), highlightthickness=1,
                     highlightbackground=theme.c("border"), highlightcolor=theme.c("border"))
    frame.pad = pad  # type: ignore[attr-defined]
    return frame


STYLES = {
    "accent": ("accent", "#10131a"),
    "green": ("green", "#062015"),
    "ghost": ("card2", "text"),
    "blue": ("blue", "#04121c"),
    "dark": ("bg2", "text"),
}


def button(parent, theme: Theme, text: str, command, style: str = "accent",
           size: int = 11, height: int = 2, width: int | None = None):
    bg_key, fg_key = STYLES.get(style, STYLES["accent"])
    fg = fg_key if fg_key.startswith("#") else theme.c(fg_key)
    btn = tk.Button(
        parent, text=text, command=command, font=theme.font(size, bold=True),
        bg=theme.c(bg_key), fg=fg, activebackground=theme.c(bg_key),
        activeforeground=fg, relief="flat", bd=0, cursor="hand2",
        highlightthickness=0, padx=12, pady=4,
        **({"height": height} if height else {}),
        **({"width": width} if width else {}),
    )
    return btn


def checkbox(parent, theme: Theme, text: str, var: tk.BooleanVar, command=None):
    return tk.Checkbutton(
        parent, text=text, variable=var, command=command, bg=parent["bg"],
        fg=theme.c("text"), activebackground=parent["bg"],
        activeforeground=theme.c("text"), selectcolor=theme.c("bg2"),
        font=theme.font(11), anchor="e", justify="right", relief="flat",
        bd=0, highlightthickness=0, cursor="hand2", padx=4,
    )


# ---------------------------------------------------------------------------
# صفحه‌ی خانه
# ---------------------------------------------------------------------------
def build_home(app, parent) -> tk.Frame:
    T = app.T
    frame = tk.Frame(parent, bg=T.c("bg"))

    app.lbl_status_title = label(frame, T, "آماده اتصال • ۱۸۰ روز اعتبار", 20, True)
    app.lbl_status_title.pack(fill="x", padx=18, pady=(12, 2))
    app.lbl_status_sub = label(frame, T, "برای اتصال لمس کنید", 12, color="muted")
    app.lbl_status_sub.pack(fill="x", padx=18)

    app.shield = ShieldButton(frame, T, command=app.on_main_button, size=330)
    app.shield.pack(pady=(6, 2))

    app.pill_ip = Pill(frame, T, "آی‌پی فعلی: —", width=470, height=40)
    app.pill_ip.pack(pady=(2, 10))

    # کارت سرورهای هوشمند
    c = card(frame, T)
    c.pack(fill="x", padx=18, pady=6)
    inner = tk.Frame(c, bg=T.c("card"))
    inner.pack(fill="x", padx=14, pady=12)

    row = tk.Frame(inner, bg=T.c("card"))
    row.pack(fill="x")
    crown = tk.Canvas(row, width=46, height=46, bg=T.c("card"), highlightthickness=0)
    crown.pack(side="left")
    round_rect(crown, 1, 1, 45, 45, r=12, fill=T.c("card2"), outline=T.c("border"))
    draw_icon(crown, "crown", 23, 23, 30, T.c("accent"))
    app.btn_home_back = IconButton(row, T, "back", command=lambda: app.show_page("servers"),
                                   size=44, bg_key="card2")
    app.btn_home_back.pack(side="left", padx=(6, 0))

    text_box = tk.Frame(row, bg=T.c("card"))
    text_box.pack(side="right", fill="x", expand=True)
    app.lbl_card_title = label(text_box, T, "سرورهای هوشمند", 13, True)
    app.lbl_card_title.pack(fill="x")
    app.lbl_card_value = label(text_box, T, "در انتظار لیست سرورها…", 10,
                              color="muted", wraplength=320)
    app.lbl_card_value.pack(fill="x", pady=(2, 0))

    # کارت جزئیات اتصال (فضای باقی‌مانده را پر می‌کند)
    d = card(frame, T)
    d.pack(fill="both", expand=True, padx=18, pady=(8, 10))
    box = tk.Frame(d, bg=T.c("card"))
    box.pack(fill="both", expand=True, padx=14, pady=12)

    head = tk.Frame(box, bg=T.c("card"))
    head.pack(fill="x")
    cv = tk.Canvas(head, width=26, height=26, bg=T.c("card"), highlightthickness=0)
    cv.pack(side="right")
    draw_icon(cv, "bolt", 13, 13, 22, T.c("accent"))
    label(head, T, "جزئیات اتصال", 12, True).pack(side="right", padx=4)

    grid = tk.Frame(box, bg=T.c("card"))
    grid.pack(fill="both", expand=True, pady=(8, 4))
    grid.grid_columnconfigure(0, weight=1)
    grid.grid_columnconfigure(1, weight=1)

    def cell(r, c, title):
        fr = tk.Frame(grid, bg=T.c("card2"), highlightthickness=1,
                      highlightbackground=T.c("border"))
        fr.grid(row=r, column=c, sticky="nsew", padx=4, pady=4)
        label(fr, T, title, 9, color="muted").pack(fill="x", padx=8, pady=(6, 0))
        val = label(fr, T, "—", 11, True)
        val.pack(fill="x", padx=8, pady=(0, 6))
        return val

    app.lbl_info = {
        "server": cell(0, 0, "سرور فعلی"),
        "country": cell(0, 1, "کشور"),
        "ping": cell(1, 0, "پینگ واقعی"),
        "uptime": cell(1, 1, "مدت اتصال"),
    }

    actions = tk.Frame(box, bg=T.c("card"))
    actions.pack(fill="x", pady=(4, 0))
    button(actions, T, "تغییر IP", app.on_switch_ip, "ghost", 10, height=1).pack(
        side="right", expand=True, fill="x", padx=3)
    button(actions, T, "تست پینگ", app.on_ping_click, "ghost", 10, height=1).pack(
        side="right", expand=True, fill="x", padx=3)
    button(actions, T, "لیست جدید", app.on_refresh_click, "ghost", 10, height=1).pack(
        side="right", expand=True, fill="x", padx=3)
    return frame


# ---------------------------------------------------------------------------
# صفحه‌ی سرورها
# ---------------------------------------------------------------------------
def build_servers(app, parent) -> tk.Frame:
    T = app.T
    frame = tk.Frame(parent, bg=T.c("bg"))

    head = tk.Frame(frame, bg=T.c("bg"))
    head.pack(fill="x", padx=18, pady=(12, 4))
    canvas = tk.Canvas(head, width=30, height=30, bg=T.c("bg"), highlightthickness=0)
    canvas.pack(side="right")
    draw_icon(canvas, "globe", 15, 15, 24, T.c("accent"))
    label(head, T, "انتخاب کشور و سرورهای هوشمند", 14, True).pack(side="right", padx=6)

    # نوار فیلتر
    bar = tk.Frame(frame, bg=T.c("bg"))
    bar.pack(fill="x", padx=18, pady=6)
    app.var_country = tk.StringVar(value="همه کشورها (All Countries)")
    app.cmb_country = ttk.Combobox(bar, textvariable=app.var_country, state="readonly",
                                   font=T.font(10), justify="right")
    app.cmb_country.pack(side="right", fill="x", expand=True, padx=(6, 0))
    try:
        app.tk.call("option", "add", "*TCombobox*Listbox.background", T.c("card"))
        app.tk.call("option", "add", "*TCombobox*Listbox.foreground", T.c("text"))
        app.tk.call("option", "add", "*TCombobox*Listbox.selectBackground", T.c("accent"))
        app.tk.call("option", "add", "*TCombobox*Listbox.selectForeground", "#10131a")
    except Exception:
        pass
    app.cmb_country.bind("<<ComboboxSelected>>", lambda _e: app.refresh_table())
    button(bar, T, "تست پینگ واقعی", app.on_ping_click, "accent", 10).pack(side="right")

    app.progress_servers = ProgressBar(frame, T, width=520, height=10)
    app.progress_servers.pack(fill="x", padx=18, pady=(4, 2))
    app.lbl_stats = label(frame, T, "کل سرورها: ۰ • تست‌شده: ۰ • فعال: ۰", 10, color="blue")
    app.lbl_stats.pack(fill="x", padx=18)

    # جدول
    table_frame = tk.Frame(frame, bg=T.c("card"), highlightthickness=1,
                           highlightbackground=T.c("border"))
    table_frame.pack(fill="both", expand=True, padx=18, pady=8)

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    app.style = style
    style.configure("MD.Treeview", background=T.c("card2"), fieldbackground=T.c("card2"),
                    foreground=T.c("text"), rowheight=26, font=T.font(10), borderwidth=0)
    style.configure("MD.Treeview.Heading", background=T.c("bg2"), foreground=T.c("muted"),
                    font=T.font(10, True), relief="flat")
    style.map("MD.Treeview.Heading", background=[("active", T.c("bg2"))])
    style.configure("TCombobox", fieldbackground=T.c("card"), background=T.c("card"),
                    foreground=T.c("text"), arrowcolor=T.c("accent"),
                    bordercolor=T.c("border"), lightcolor=T.c("card"),
                    darkcolor=T.c("card"), selectbackground=T.c("card"),
                    selectforeground=T.c("text"), padding=6)
    style.map("TCombobox", fieldbackground=[("readonly", T.c("card"))],
              foreground=[("readonly", T.c("text"))])
    style.configure("Vertical.TScrollbar", background=T.c("card2"),
                    troughcolor=T.c("bg2"), bordercolor=T.c("bg2"),
                    arrowcolor=T.c("muted"))

    cols = ("status", "country", "ping", "host")
    app.tree = ttk.Treeview(table_frame, columns=cols, show="headings",
                            style="MD.Treeview", height=12)
    heads = {"status": "وضعیت", "country": "کشور", "ping": "پینگ", "host": "آدرس سرور"}
    widths = {"status": 80, "country": 130, "ping": 80, "host": 250}
    for col in cols:
        app.tree.heading(col, text=heads[col])
        app.tree.column(col, width=widths[col], anchor="center" if col != "host" else "w")
    app.tree.tag_configure("alive", foreground=T.c("green"))
    app.tree.tag_configure("dead", foreground=T.c("muted"))
    app.tree.tag_configure("online", foreground=T.c("accent"))
    app.tree.pack(side="right", fill="both", expand=True, padx=(0, 2), pady=2)
    sb = ttk.Scrollbar(table_frame, orient="vertical", command=app.tree.yview)
    sb.pack(side="right", fill="y")
    app.tree.configure(yscrollcommand=sb.set)
    app.tree.bind("<Double-1>", app.on_tree_double_click)

    btns = tk.Frame(frame, bg=T.c("bg"))
    btns.pack(fill="x", padx=18, pady=(2, 12))
    button(btns, T, "* اتصال هوشمند به سریع‌ترین سرور", app.on_connect_best,
           "green", 11).pack(fill="x", pady=3)
    button(btns, T, "دریافت لیست جدید", app.on_refresh_click, "dark", 11).pack(fill="x", pady=3)
    return frame


# ---------------------------------------------------------------------------
# صفحه‌ی خرید (نمایشی)
# ---------------------------------------------------------------------------
PLANS = [
    ("اقتصادی", "اشتراک ۱ ماهه", "۳۰ روز نامحدود", "۳ تراکنش دلار", "blue"),
    ("پرفروش", "اشتراک ۳ ماهه", "۹۰ روز نامحدود", "۷ تراکنش دلار", "accent"),
    ("پیشنهاد ویژه", "اشتراک ۶ ماهه", "۱۸۰ روز نامحدود", "۱۱ تراکنش دلار", "green"),
    ("یکساله طلایی", "اشتراک ۱ ساله", "۳۶۵ روز نامحدود", "۱۸ تراکنش دلار", "accent"),
]


def build_shop(app, parent) -> tk.Frame:
    T = app.T
    frame = tk.Frame(parent, bg=T.c("bg"))

    c = card(frame, T)
    c.pack(fill="x", padx=18, pady=(12, 6))
    inner = tk.Frame(c, bg=T.c("card"))
    inner.pack(fill="x", padx=14, pady=12)
    label(inner, T, " اشتراک ویژه فعال • ۱۸۰ روز اعتبار باقی‌مانده", 12, True,
          color="green").pack(fill="x")
    row = tk.Frame(inner, bg=T.c("card"))
    row.pack(fill="x", pady=(8, 0))
    label(row, T, f"کد یکتای دستگاه: {app.device_id}", 10, color="muted").pack(side="right")
    button(row, T, "پشتیبانی", app.open_telegram, "ghost", 9, height=1).pack(side="left")
    label(frame, T, "این صفحه نمایشی است؛ برای خرید واقعی از پشتیبانی پیام بگیر.",
          9, color="muted").pack(fill="x", padx=18)

    grid = tk.Frame(frame, bg=T.c("bg"))
    grid.pack(fill="x", padx=18, pady=6)
    for i, (title, sub, days, price, color) in enumerate(PLANS):
        cc = card(grid, T)
        cc.grid(row=i // 2, column=1 - (i % 2), sticky="nsew", padx=5, pady=5)
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        box = tk.Frame(cc, bg=T.c("card"))
        box.pack(fill="both", expand=True, padx=12, pady=10)
        top = tk.Frame(box, bg=T.c("card"))
        top.pack(fill="x")
        cv = tk.Canvas(top, width=30, height=30, bg=T.c("card"), highlightthickness=0)
        cv.pack(side="left")
        draw_icon(cv, "diamond", 15, 15, 26, T.c(color))
        label(top, T, title, 12, True, color=color).pack(side="right")
        label(box, T, sub, 10).pack(fill="x", pady=(6, 0))
        label(box, T, days, 9, color="muted").pack(fill="x")
        label(box, T, f"قیمت: {price}", 10, True, color="accent").pack(fill="x", pady=(6, 0))
        button(box, T, "خرید / تمدید", lambda: app.toast("نسخه‌ی نمایشی: پرداخت غیرفعال است"),
               "ghost", 9, height=1).pack(fill="x", pady=(8, 0))

    pay = card(frame, T)
    pay.pack(fill="x", padx=18, pady=6)
    pin = tk.Frame(pay, bg=T.c("card"))
    pin.pack(fill="x", padx=14, pady=12)
    label(pin, T, "پرداخت با ارز دیجیتال (TRC20)", 12, True).pack(fill="x")
    addr_row = tk.Frame(pin, bg=T.c("card"))
    addr_row.pack(fill="x", pady=6)
    addr_lbl = tk.Label(addr_row, text="TZ6XSBGTEAfwKw4KGNDPcNQBHBSe5pEX6A",
                        bg=T.c("bg2"), fg=T.c("text"), font=("Consolas", 9),
                        padx=8, pady=6)
    addr_lbl.pack(side="right", fill="x", expand=True)
    button(addr_row, T, "کپی", app.copy_wallet, "dark", 9, height=1).pack(side="left")
    button(pin, T, "ارسال رسید و کد دستگاه در تلگرام", app.open_telegram, "blue", 10
           ).pack(fill="x", pady=(6, 0))
    return frame


# ---------------------------------------------------------------------------
# صفحه‌ی تنظیمات
# ---------------------------------------------------------------------------
def build_settings(app, parent) -> tk.Frame:
    T = app.T
    frame = tk.Frame(parent, bg=T.c("bg"))
    label(frame, T, "تنظیمات پیشرفته", 14, True).pack(fill="x", padx=18, pady=(12, 6))

    c = card(frame, T)
    c.pack(fill="x", padx=18, pady=4)
    inner = tk.Frame(c, bg=T.c("card"))
    inner.pack(fill="x", padx=14, pady=12)

    row = tk.Frame(inner, bg=T.c("card"))
    row.pack(fill="x")
    label(row, T, "زمان انتظار هر سرور (تایم‌اوت):", 11).pack(side="right")
    app.var_timeout = tk.StringVar(value=str(int(app.controller.s.get("ping_timeout") or 2)))
    cmb = ttk.Combobox(row, textvariable=app.var_timeout, state="readonly", width=6,
                       values=["1", "2", "3", "5"], font=T.font(10), justify="center")
    cmb.pack(side="left")
    cmb.bind("<<ComboboxSelected>>", lambda _e: app.save_setting("ping_timeout",
                                                                 float(app.var_timeout.get())))

    app.var_only443 = tk.BooleanVar(value=bool(app.controller.s.get("only_port_443")))
    app.var_autoreconnect = tk.BooleanVar(value=bool(app.controller.s.get("auto_reconnect")))
    app.var_autostart = tk.BooleanVar(value=bool(app.controller.s.get("connect_on_start")))
    app.var_split = tk.BooleanVar(value=bool(app.controller.s.get("split_tunneling")))
    app.var_autoping = tk.BooleanVar(value=bool(app.controller.s.get("auto_ping_after_fetch")))

    opts = [
        ("فقط سرورهای پورت ۴۴۳ (لازمه‌ی ویندوز)", app.var_only443, "only_port_443"),
        ("اتصال مجدد خودکار در صورت قطعی", app.var_autoreconnect, "auto_reconnect"),
        ("اتصال خودکار هنگام اجرای برنامه", app.var_autostart, "connect_on_start"),
        ("تست خودکار پینگ بعد از دریافت لیست", app.var_autoping, "auto_ping_after_fetch"),
        ("Split Tunneling (عدم تغییر مسیر پیش‌فرض)", app.var_split, "split_tunneling"),
    ]
    for text, var, key in opts:
        checkbox(inner, T, text, var, command=lambda k=key, v=var: app.save_setting(k, bool(v.get()))
                 ).pack(fill="x", pady=2)

    tools = tk.Frame(inner, bg=T.c("card"))
    tools.pack(fill="x", pady=(8, 0))
    button(tools, T, "بررسی موتور اتصال", app.on_preflight, "ghost", 10, height=1
           ).pack(side="right", padx=3)
    button(tools, T, "پاک کردن کش", app.on_clear_cache, "ghost", 10, height=1
           ).pack(side="right", padx=3)
    button(tools, T, "نسخه‌ی برنامه: " + config.VERSION, lambda: None, "dark", 9, height=1
           ).pack(side="left", padx=3)

    label(frame, T, "گزارش زنده‌ی عملیات (Live log):", 11, True).pack(
        fill="x", padx=18, pady=(8, 4))
    log_frame = tk.Frame(frame, bg=T.c("log_bg"), highlightthickness=1,
                         highlightbackground=T.c("border"))
    log_frame.pack(fill="both", expand=True, padx=18, pady=(0, 12))
    app.txt_log = tk.Text(log_frame, bg=T.c("log_bg"), fg="#cfe0ff", bd=0,
                          font=("Consolas", 9), wrap="word",
                          insertbackground=T.c("text"), padx=8, pady=6)
    app.txt_log.tag_configure("rtl", justify="right")
    app.txt_log.pack(side="right", fill="both", expand=True)
    sb = ttk.Scrollbar(log_frame, orient="vertical", command=app.txt_log.yview)
    sb.pack(side="right", fill="y")
    app.txt_log.configure(yscrollcommand=sb.set, state="disabled")
    return frame
