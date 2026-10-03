"""تست پینگ واقعی (TCP) و گرفتن IP فعلی."""
from __future__ import annotations

import socket
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional

from .sources import Server

IP_APIS = [
    "https://api.ipify.org",
    "https://ipinfo.io/ip",
    "https://icanhazip.com",
    "https://api.myip.com",
]


def tcp_ping(host: str, port: int = 443, timeout: float = 2.0) -> Optional[float]:
    """زمان برقراری اتصال TCP به میلی‌ثانیه (None = بی‌پاسخ)."""
    try:
        t0 = time.perf_counter()
        with socket.create_connection((host, port), timeout=timeout):
            return (time.perf_counter() - t0) * 1000.0
    except Exception:
        return None


def ping_servers(
    servers: list[Server],
    timeout: float = 2.0,
    workers: int = 64,
    limit: int | None = None,
    on_result: Callable[[Server, int, int], None] | None = None,
    stop_event: threading.Event | None = None,
) -> None:
    """پینگ موازی؛ نتیجه داخل خودِ Server نوشته می‌شود."""
    targets = servers if limit in (None, 0) else servers[:limit]
    total = len(targets)
    done = 0
    lock = threading.Lock()

    def work(s: Server):
        nonlocal done
        if stop_event is not None and stop_event.is_set():
            return
        lat = tcp_ping(s.host, s.port, timeout)
        s.latency = lat
        s.alive = lat is not None
        with lock:
            done += 1
            cur = done
        if on_result:
            try:
                on_result(s, cur, total)
            except Exception:
                pass

    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        list(ex.map(work, targets))


def get_public_ip(timeout: float = 6.0) -> Optional[str]:
    for url in IP_APIS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MDavariVPN/2.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                text = resp.read().decode("utf-8", "replace").strip()
            if text and len(text) < 60:
                if url.endswith("myip.com"):
                    import json as _json
                    try:
                        text = _json.loads(text).get("ip", text)
                    except Exception:
                        continue
                return text
        except Exception:
            continue
    return None
