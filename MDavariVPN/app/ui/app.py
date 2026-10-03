"""پنجره‌ی اصلی برنامه."""
from __future__ import annotations

import os
import platform
import subprocess
import sys
import time
import tkinter as tk
import uuid
import webbrowser
from tkinter import messagebox, ttk

from .. import config
from ..controller import Controller
from ..sources import COUNTRY_FA, Server
from .pages import build_home, build_servers, build_settings, build_shop, label
from .theme import Theme
from .widgets import IconButton, NavBar, draw_icon, round_rect

TELEGRAM_URL = "https://t.me/"


class App(tk.Tk):
    def __init__(self, settings: config.Settings | None = None):
        super().__init__()
        self.settings = settings or config.Settings()
        self.T = Theme(self.settings.get("theme", "dark"))
        self.title("MDavari VPN PRO — Smart SSTP Client v2.0")
        self.geometry("620x1020")
        self.minsize(560, 800)
        self.configure(bg=self.T.c("bg"))
        self.device_id = self._device_id()
        self.controller = Controller(self.settings)
        self.pages: dict[str, tk.Frame] = {}
        self.tree_rows: dict[str, str] = {}
        self.current_page = "home"
        self.auto_retry_messages = True
        self._build_ui()
        self.controller.start()
        self.after(150, self._pump)
        self.after(1000, self._tick)
        self.after(60, self._animate)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.show_page("home")
        self.append_log("* MDavari VPN v%s آماده است" % config.VERSION)
        ok, msg = self.controller.engine.preflight()
        if not ok and msg:
            self.append_log(f"! {msg}")

    # ------------------------------------------------------------------
    # ساخت رابط
    # ------------------------------------------------------------------
    def _device_id(self) -> str:
        path = config.data_dir() / "device_id.txt"
        try:
            if path.exists():
                return path.read_text(encoding="utf-8").strip()
            did = "MD-" + str(uuid.uuid4())[:8].upper()
            path.write_text(did, encoding="utf-8")
            return did
        except Exception:
            return "MD-DEMO0000"

    def _build_ui(self) -> None:
        T = self.T
        # هدر
        self.header = tk.Frame(self, bg=T.c("bg"))
        self.header.pack(fill="x", padx=14, pady=(10, 4))
        self.btn_theme = IconButton(self.header, T, "sun", command=self.toggle_theme, size=46)
        self.btn_theme.pack(side="left", padx=(0, 6))
        self.btn_tg = IconButton(self.header, T, "plane", command=self.open_telegram, size=46)
        self.btn_tg.pack(side="left")

        logo = tk.Frame(self.header, bg=T.c("bg"))
        logo.pack(side="right")
        cv = tk.Canvas(logo, width=40, height=44, bg=T.c("bg"), highlightthickness=0)
        cv.pack(side="right", padx=(6, 0))
        draw_icon(cv, "shield", 20, 22, 40, T.c("accent"))
        tk.Label(logo, text="MDavari VPN", bg=T.c("bg"), fg=T.c("text"),
                 font=T.font(17, bold=True)).pack(side="right")

        badge = tk.Canvas(self.header, width=78, height=30, bg=T.c("bg"),
                          highlightthickness=0)
        badge.pack(side="right", padx=8)
        round_rect(badge, 1, 1, 77, 29, r=14, fill=T.c("green_dark"),
                   outline=T.c("green"), width=1)
        badge.create_text(39, 15, text="VIP PRO", fill=T.c("green"),
                          font=T.font(9, bold=True))

        # نوار پایین
        self.navbar = NavBar(self, T, on_select=self.show_page)
        self.navbar.pack(side="bottom", fill="x", pady=(0, 6))

        # ظرف صفحات
        self.container = tk.Frame(self, bg=T.c("bg"))
        self.container.pack(fill="both", expand=True)

        self.pages = {
            "home": build_home(self, self.container),
            "servers": build_servers(self, self.container),
            "shop": build_shop(self, self.container),
            "settings": build_settings(self, self.container),
        }

    def _rebuild_ui(self) -> None:
        page = self.current_page
        for w in (self.header, self.navbar, self.container):
            w.destroy()
        self._build_ui()
        self.show_page(page)
        # بازسازی محتوای جدول و لاگ
        self.refresh_table()
        self.update_stats()

    def show_page(self, name: str) -> None:
        if name not in self.pages:
            return
        self.current_page = name
        for page in self.pages.values():
            page.pack_forget()
        self.pages[name].pack(fill="both", expand=True)
        self.navbar.set_active(name)
        if name == "servers":
            self.refresh_table()

    # ------------------------------------------------------------------
    # رویدادها
    # ------------------------------------------------------------------
    def on_main_button(self) -> None:
        c = self.controller
        if c.state in ("connecting", "fetching", "pinging", "disconnecting"):
            self.toast("لطفاً تا پایان عملیات جاری صبر کن")
            return
        if c.connected_server is not None:
            c.disconnect()
        else:
            if not c.servers:
                self.show_page("servers")
                self.toast("اول لیست سرورها را دریافت می‌کنیم…")
                c.refresh_servers()
                return
            c.connect_best()

    def on_connect_best(self) -> None:
        if not self.controller.servers:
            self.toast("لیست سرورها خالی است؛ «دریافت لیست جدید» را بزن")
            return
        self.controller.connect_best()

    def on_ping_click(self) -> None:
        if self.controller.state == "pinging":
            self.controller.stop_ping()
            self.toast("تست پینگ متوقف شد")
            return
        if not self.controller.servers:
            self.toast("اول لیست سرورها را دریافت کن")
            return
        self.controller.ping_all()

    def on_refresh_click(self) -> None:
        self.controller.refresh_servers()

    def on_switch_ip(self) -> None:
        if self.controller.connected_server is None:
            self.toast("اول وصل شو، بعد IP را عوض کن")
            return
        self.controller.switch_ip()

    def on_tree_double_click(self, event) -> None:
        item = self.tree.identify_row(event.y)
        if not item:
            return
        key = self.tree_rows.get(item)
        for s in self.controller.servers:
            if s.key == key:
                self.controller.connect(s)
                return

    def on_preflight(self) -> None:
        ok, msg = self.controller.engine.preflight()
        self.append_log(("✓ " if ok else "! ") + (msg or "موتور اتصال آماده است"))
        self.toast("موتور اتصال آماده است" if ok else (msg or "موتور اتصال آماده نیست"))

    def on_clear_cache(self) -> None:
        try:
            if config.CACHE_FILE.exists():
                config.CACHE_FILE.unlink()
            self.append_log("🧹 کش سرورها پاک شد")
            self.toast("کش پاک شد")
        except Exception as e:  # noqa: BLE001
            self.append_log(f"! پاک کردن کش ناموفق: {e}")

    def save_setting(self, key: str, value) -> None:
        self.settings.set(key, value)
        self.append_log(f"# تنظیم «{key}» = {value}")

    def toggle_theme(self) -> None:
        mode = self.T.toggle()
        self.settings.set("theme", mode)
        self.configure(bg=self.T.c("bg"))
        self._rebuild_ui()

    def open_telegram(self) -> None:
        try:
            webbrowser.open(TELEGRAM_URL)
            self.toast("کانال تلگرام باز شد")
        except Exception:
            self.toast("باز کردن تلگرام ناموفق بود")

    def copy_wallet(self) -> None:
        try:
            self.clipboard_clear()
            self.clipboard_append("TZ6XSBGTEAfwKw4KGNDPcNQBHBSe5pEX6A")
            self.toast("آدرس کپی شد")
        except Exception:
            self.toast("کپی ناموفق")

    def toast(self, text: str, ms: int = 2600) -> None:
        old = getattr(self, "_toast_lbl", None)
        if old is not None:
            try:
                old.destroy()
            except Exception:
                pass
        lbl = tk.Label(self, text=text, bg=self.T.c("card2"), fg=self.T.c("text"),
                       font=self.T.font(10), padx=14, pady=8, bd=0)
        lbl.place(relx=0.5, rely=0.945, anchor="center")
        self._toast_lbl = lbl
        self.after(ms, lambda: lbl.winfo_exists() and lbl.destroy())

    # ------------------------------------------------------------------
    # حلقه‌های به‌روزرسانی
    # ------------------------------------------------------------------
    def _pump(self) -> None:
        try:
            while True:
                kind, payload = self.controller.events.get_nowait()
                if kind == "log":
                    self.append_log(str(payload))
                elif kind == "state":
                    self._apply_state(payload)
                elif kind == "servers":
                    self.servers_data = payload
                    self.update_stats()
                    self.refresh_table()
                    self._update_home_card()
                elif kind == "ping":
                    self._update_ping(payload)
                elif kind == "ip":
                    self._update_ip(str(payload))
        except Exception:
            pass
        self.after(150, self._pump)

    def _tick(self) -> None:
        """به‌روزرسانی ثانیه‌شمار و متن‌های وضعیت."""
        c = self.controller
        if c.connected_server is not None and c.connected_at:
            secs = int(time.time() - c.connected_at)
            self.pill_ip.set_text(
                f" {config.fa_digits(config.human_uptime(secs))}  •  "
                f"IP: {c.public_ip or '—'}", "green")
            self.lbl_status_sub.configure(
                text=f"برای قطع لمس کنید • زمان متصل به {secs} ثانیه")
        self._update_home_card()
        self._fill_info()
        self.after(1000, self._tick)

    def _animate(self) -> None:
        try:
            self.shield.tick()
        except Exception:
            pass
        self.after(70, self._animate)

    # ------------------------------------------------------------------
    # به‌روزرسانی اجزا
    # ------------------------------------------------------------------
    def _apply_state(self, payload: dict) -> None:
        state = payload.get("state", "idle")
        server: Server | None = payload.get("server")
        titles = {
            "idle": "آماده اتصال • ۱۸۰ روز اعتبار",
            "fetching": "در حال دریافت لیست سرورها…",
            "pinging": "تست پینگ سرورها…",
            "connecting": "در حال اتصال…",
            "disconnecting": "در حال قطع اتصال…",
        }
        subs = {
            "idle": "برای اتصال لمس کنید",
            "fetching": "چند لحظه صبر کن",
            "pinging": "پینگ واقعی همه‌ی سرورها گرفته می‌شود",
            "connecting": (server.label if server else ""),
            "disconnecting": "لطفاً صبر کن",
        }
        if state == "connected" and server is not None:
            self.lbl_status_title.configure(text="متصل و ایمن", fg=self.T.c("green"))
            self.lbl_status_sub.configure(text="برای قطع لمس کنید")
            self.shield.set_state("connected", "PROTECTED")
            self.pill_ip.set_text(f"IP: {self.controller.public_ip or '—'}", "green")
        else:
            self.lbl_status_title.configure(
                text=titles.get(state, "آماده اتصال • ۱۸۰ روز اعتبار"),
                fg=self.T.c("accent") if state in ("connecting", "fetching", "pinging")
                else self.T.c("text"))
            self.lbl_status_sub.configure(text=subs.get(state, ""))
            sub_map = {"idle": "START VPN", "fetching": "FETCHING", "pinging": "TESTING",
                       "connecting": "CONNECTING", "disconnecting": "STOPPING"}
            self.shield.set_state(state, sub_map.get(state, "START VPN"))
            if state == "idle" and self.controller.public_ip:
                self.pill_ip.set_text(f"آی‌پی فعلی: {self.controller.public_ip}", "border")
        self._update_home_card()

    def _fill_info(self) -> None:
        c = self.controller
        if not hasattr(self, "lbl_info"):
            return
        srv = c.connected_server
        self.lbl_info["server"].configure(text=srv.label if srv else "—")
        self.lbl_info["country"].configure(text=srv.country_fa if srv else "—")
        if srv is not None and srv.latency is not None:
            self.lbl_info["ping"].configure(text=f"{int(srv.latency)} ms")
        elif srv is not None and srv.ping_ms is not None:
            self.lbl_info["ping"].configure(text=f"{srv.ping_ms} ms")
        else:
            self.lbl_info["ping"].configure(text="—")
        if srv is not None and c.connected_at:
            secs = int(time.time() - c.connected_at)
            self.lbl_info["uptime"].configure(text=config.human_uptime(secs))
        else:
            self.lbl_info["uptime"].configure(text="—")

    def _update_home_card(self) -> None:
        c = self.controller
        if not hasattr(self, "lbl_card_value"):
            return
        if c.connected_server is not None:
            secs = int(time.time() - c.connected_at) if c.connected_at else 0
            self.lbl_card_title.configure(text="سرور متصل کنونی", fg=self.T.c("green"))
            self.lbl_card_value.configure(
                text=f"متصل به: {c.connected_server.label} • مدت {secs} ثانیه")
        else:
            alive = len([s for s in c.servers if s.alive])
            timeout = int(self.settings.get("connect_timeout") or 60)
            self.lbl_card_title.configure(text="سرورهای هوشمند", fg=self.T.c("text"))
            self.lbl_card_value.configure(
                text=f"اتصال خودکار • {config.fa_digits(len(c.servers))} سرور • {config.fa_digits(alive)} فعال • تایم‌اوت {config.fa_digits(timeout)} ثانیه")

    def _update_ping(self, payload: dict) -> None:
        done, total = payload.get("done", 0), max(1, payload.get("total", 1))
        self.progress_servers.set(done / total)
        self.update_stats(done=done, total=total)

    def _update_ip(self, ip: str) -> None:
        c = self.controller
        if c.connected_server is not None:
            self.pill_ip.set_text(f"IP: {ip}", "green")
        else:
            self.pill_ip.set_text(f"آی‌پی فعلی: {ip}", "border")

    def update_stats(self, done: int | None = None, total: int | None = None) -> None:
        if not hasattr(self, "lbl_stats"):
            return
        c = self.controller
        tested = done if done is not None else c.tested
        ttl = total if total is not None else (len(c.servers) or 0)
        alive = len([s for s in c.servers if s.alive])
        self.lbl_stats.configure(
            text=f"کل سرورها: {config.fa_digits(len(c.servers))}  •  "
                 f"تست‌شده: {config.fa_digits(tested)}/{config.fa_digits(ttl)}  •  "
                 f"فعال: {config.fa_digits(alive)}")
        if done is None:
            self.progress_servers.set(0 if not c.servers else alive / max(1, len(c.servers)))

    def refresh_table(self) -> None:
        if not hasattr(self, "tree"):
            return
        tree = self.tree
        for item in tree.get_children():
            tree.delete(item)
        self.tree_rows.clear()
        country_filter = getattr(self, "var_country", None)
        wanted = country_filter.get() if country_filter else "همه کشورها (All Countries)"
        servers = list(self.controller.servers)
        if wanted and not wanted.startswith("همه"):
            servers = [s for s in servers if s.country_fa == wanted or s.country == wanted]
        servers.sort(key=lambda s: (s.latency if s.latency is not None else 9e9,
                                    s.ping_ms if s.ping_ms is not None else 9e9))
        current = self.controller.connected_server
        for s in servers[:500]:
            if current is not None and s.key == current.key:
                status, tag = "● متصل", "online"
            elif s.alive is True:
                status, tag = "فعال", "alive"
            elif s.alive is False:
                status, tag = "بی‌پاسخ", "dead"
            else:
                status, tag = "—", "dead"
            ping = f"{int(s.latency)} ms" if s.latency is not None else \
                (f"{s.ping_ms} ms" if s.ping_ms is not None else "—")
            item = tree.insert("", "end", values=(status, s.country_fa, ping, s.label),
                               tags=(tag,))
            self.tree_rows[item] = s.key
        # پرکردن فیلتر کشورها
        if country_filter is not None:
            names = ["همه کشورها (All Countries)"] + sorted(
                {s.country_fa for s in self.controller.servers if s.country_fa})
            self.cmb_country.configure(values=names)
            if wanted not in names:
                self.var_country.set(names[0])

    def append_log(self, text: str) -> None:
        if not hasattr(self, "txt_log"):
            return
        line = f"[{config.now_str()}] {text}"
        try:
            self.txt_log.configure(state="normal")
            self.txt_log.insert("end", line + "\n", "rtl")
            limit = int(self.settings.get("log_lines") or 400)
            if int(self.txt_log.index("end-1c").split(".")[0]) > limit:
                self.txt_log.delete("1.0", "2.0")
            self.txt_log.see("end")
            self.txt_log.configure(state="disabled")
        except Exception:
            pass

    # ------------------------------------------------------------------
    def on_close(self) -> None:
        try:
            self.settings.save()
            self.controller.stop()
            if self.controller.connected_server is not None:
                if messagebox.askyesno("MDavari VPN", "اتصال VPN باز است. بسته شود؟"):
                    self.controller.engine.disconnect()
        except Exception:
            pass
        self.destroy()


def run() -> None:
    app = App()
    app.mainloop()
