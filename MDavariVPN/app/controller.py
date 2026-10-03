"""مغز برنامه: هماهنگی گرفتن لیست، پینگ، اتصال و اتصال مجدد خودکار."""
from __future__ import annotations

import queue
import threading
import time
from typing import Callable, Optional

from . import config, pinger, sources
from .engine import BaseEngine, build_engine
from .sources import Server

STATES = ("idle", "fetching", "pinging", "connecting", "connected", "disconnecting")


class Controller:
    """همه‌ی کارهای شبکه‌ای در نخ‌های جدا انجام می‌شود و رویدادها در صف UI می‌روند."""

    def __init__(self, settings: config.Settings):
        self.s = settings
        self.events: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self.servers: list[Server] = []
        self.state = "idle"
        self.connected_server: Server | None = None
        self.connected_at: float = 0.0
        self.public_ip: str | None = None
        self.last_error = ""
        self.tested = 0
        self.alive = 0
        self._stop = threading.Event()
        self._ping_stop = threading.Event()
        self._busy = threading.Event()
        self.engine: BaseEngine = build_engine(self.log)
        self._threads: list[threading.Thread] = []
        self._session_start = time.time()

    # --- رویداد -----------------------------------------------------------
    def emit(self, kind: str, payload=None) -> None:
        self.events.put((kind, payload))

    def log(self, text: str) -> None:
        self.emit("log", text)

    # --- چرخه‌ی عمر --------------------------------------------------------
    def start(self) -> None:
        for fn in (self._boot, self._monitor_loop, self._ip_loop):
            t = threading.Thread(target=fn, daemon=True)
            t.start()
            self._threads.append(t)

    def stop(self) -> None:
        self._stop.set()
        self._ping_stop.set()

    def _boot(self) -> None:
        cached = sources.load_cache()
        if cached:
            self.servers = cached
            self.log(f"~ {len(cached)} سرور از حافظه‌ی قبلی بارگذاری شد")
            self.emit("servers", self.snapshot())
        self.refresh_servers()
        if self.s.get("connect_on_start"):
            self.connect_best()

    # --- لیست سرورها --------------------------------------------------------
    def refresh_servers(self) -> None:
        if self._busy.is_set():
            return
        self.set_state("fetching")

        def work():
            try:
                servers, report = sources.refresh(
                    self.log,
                    only_port_443=bool(self.s.get("only_port_443")),
                    use_headless=True,
                    do_geo=True,
                )
                if servers:
                    self.servers = servers
                    self.tested = self.alive = 0
                    self.emit("servers", self.snapshot())
                    if self.s.get("auto_ping_after_fetch"):
                        self.ping_all()
            finally:
                if self.state == "fetching":
                    self.set_state("connected" if self.connected_server else "idle")

        threading.Thread(target=work, daemon=True).start()

    def snapshot(self) -> dict:
        return {
            "servers": self.servers,
            "tested": self.tested,
            "alive": self.alive,
            "state": self.state,
            "connected": self.connected_server,
            "public_ip": self.public_ip,
            "session": int(time.time() - self._session_start),
        }

    # --- پینگ --------------------------------------------------------------
    def ping_all(self) -> None:
        if not self.servers:
            self.log("i لیستی برای تست وجود ندارد")
            return
        self._ping_stop.clear()
        self.set_state("pinging")
        limit = int(self.s.get("ping_top") or 0) or None

        def work():
            total = len(self.servers[:limit] if limit else self.servers)
            self.log(f"> تست پینگ واقعی روی {total} سرور …")

            def on_result(server: Server, done: int, _total: int):
                self.tested = done
                if server.alive:
                    self.alive += 1
                if done % 5 == 0 or done == _total:
                    self.emit("ping", {"done": done, "total": _total, "server": server})
            try:
                self.alive = 0
                pinger.ping_servers(
                    self.servers,
                    timeout=float(self.s.get("ping_timeout") or 2.0),
                    workers=int(self.s.get("ping_workers") or 64),
                    limit=limit,
                    on_result=on_result,
                    stop_event=self._ping_stop,
                )
                alive = [s for s in self.servers if s.alive]
                self.log(f"✓ {len(alive)} سرورِ فعال از {self.tested} سرورِ تست‌شده")
                self.emit("servers", self.snapshot())
            finally:
                if self.state == "pinging":
                    self.set_state("connected" if self.connected_server else "idle")

        threading.Thread(target=work, daemon=True).start()

    def stop_ping(self) -> None:
        self._ping_stop.set()

    # --- انتخاب بهترین سرور ------------------------------------------------
    def best_servers(self, exclude: set[str] | None = None) -> list[Server]:
        exclude = exclude or set()
        pool = [s for s in self.servers
                if s.alive and s.key not in exclude and s.port == 443]
        if not pool:
            pool = [s for s in self.servers
                    if s.alive is not False and s.key not in exclude and s.port == 443]
        pool.sort(key=lambda s: (s.latency if s.latency is not None else 9e9,
                                 s.ping_ms if s.ping_ms is not None else 9e9))
        return pool

    # --- اتصال -------------------------------------------------------------
    def connect_best(self, exclude: set[str] | None = None) -> None:
        """اتصال هوشمند: چند سرور برتر را امتحان می‌کند تا یکی وصل شود."""
        pool = self.best_servers(exclude=exclude)
        if not pool:
            self.log("✗ سرور مناسبی پیدا نشد؛ اول «دریافت لیست جدید» را بزن")
            return
        if self._busy.is_set():
            return

        def work():
            tried: set[str] = set(exclude or ())
            max_tries = 6
            for i in range(max_tries):
                candidates = self.best_servers(exclude=tried)
                if not candidates:
                    break
                srv = candidates[0]
                tried.add(srv.key)
                self.log(f"* تلاش {i + 1} از {max_tries}: {srv.label}"
                         + (f" ({srv.latency:.0f}ms)" if srv.latency else ""))
                ok, msg = self._do_connect(srv)
                if ok:
                    return
                srv.alive = False
                self.log(f"← {srv.label} ناموفق بود: {msg}")
                self.emit("servers", self.snapshot())
            self.log("✗ همه‌ی تلاش‌ها ناموفق بود؛ لیست را به‌روز کن یا سرور دیگری انتخاب کن")
            self.last_error = "اتصال ناموفق"
            self.set_state("idle")

        threading.Thread(target=work, daemon=True).start()

    def connect(self, server: Server | None = None) -> None:
        if server is None:
            self.connect_best()
            return
        if self._busy.is_set():
            return

        def work():
            self._do_connect(server)

        threading.Thread(target=work, daemon=True).start()

    def _do_connect(self, server: Server) -> tuple[bool, str]:
        self._busy.set()
        try:
            if self.connected_server is not None:
                self.engine.disconnect()
                self.connected_server = None
            self.set_state("connecting", server)
            ok, msg = self.engine.connect(
                server, split_tunneling=bool(self.s.get("split_tunneling")))
            if ok:
                self.connected_server = server
                self.connected_at = time.time()
                self.s.set("last_server", server.key)
                self.log(f"✓ متصل شد → {server.label} ({server.country or 'نامشخص'})")
                self.set_state("connected", server)
                self.refresh_ip()
                return True, msg
            self.log(f"! اتصال ناموفق: {msg}")
            self.last_error = msg
            self.set_state("idle")
            return False, msg
        finally:
            self._busy.clear()

    def disconnect(self, manual: bool = True) -> None:
        def work():
            self._busy.set()
            try:
                self.set_state("disconnecting")
                self.engine.disconnect()
                self.connected_server = None
                self.connected_at = 0.0
                self.log("✗ اتصال قطع شد" if manual else "✗ اتصال به‌صورت خودکار قطع شد")
                self.set_state("idle")
            finally:
                self._busy.clear()

        threading.Thread(target=work, daemon=True).start()

    def switch_ip(self) -> None:
        """قطع و اتصال به سرور بعدی (تغییر IP)."""
        exclude = {self.connected_server.key} if self.connected_server else set()
        pool = [s for s in self.best_servers(exclude=exclude)]
        if not pool:
            self.log("i سرور دیگری برای تغییر IP نیست")
            return
        target = pool[0]
        self.log(f"… تغییر IP → {target.label}")
        self.connect(target)

    # --- IP و مانیتور -------------------------------------------------------
    def refresh_ip(self) -> None:
        def work():
            ip = pinger.get_public_ip()
            if ip:
                self.public_ip = ip
                self.emit("ip", ip)

        threading.Thread(target=work, daemon=True).start()

    def _ip_loop(self) -> None:
        while not self._stop.is_set():
            self.refresh_ip()
            self._stop.wait(20 if self.connected_server else 90)

    def _monitor_loop(self) -> None:
        """مراقب اتصال: اگر تونل افتاد، خودکار وصل کن + گارد تایم‌اوت اتصال."""
        while not self._stop.is_set():
            self._stop.wait(5)
            if self._stop.is_set():
                break
            if self.state == "connecting":
                if time.time() - getattr(self, "_connect_started", 0) > \
                        float(self.s.get("connect_timeout") or 60):
                    self.log("! زمان اتصال به پایان رسید")
                    self.set_state("idle")
            if self.connected_server is not None and not self._busy.is_set():
                st = self.engine.status()
                if st == "disconnected":
                    self.log("- اتصال افتاد؛ تلاش برای وصل مجدد…")
                    self.connected_server = None
                    if self.s.get("auto_reconnect"):
                        self.connect_best()
                    else:
                        self.set_state("idle")

    # --- وضعیت -------------------------------------------------------------
    def set_state(self, state: str, server: Server | None = None) -> None:
        if state == "connecting":
            self._connect_started = time.time()
        self.state = state
        self.emit("state", {
            "state": state,
            "server": server if server is not None else self.connected_server,
            "connected_at": self.connected_at,
            "public_ip": self.public_ip,
        })
