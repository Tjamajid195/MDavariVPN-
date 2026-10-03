"""تنظیمات، مسیرها و ابزارهای پایه‌ی برنامه."""
from __future__ import annotations

import json
import os
import pathlib
import sys
import time

APP_NAME = "MDavariVPN"
VERSION = "2.0.0"
IS_WINDOWS = sys.platform.startswith("win")


def data_dir() -> pathlib.Path:
    """پوشه‌ی داده‌های برنامه (تنظیمات، کش، لاگ)."""
    if IS_WINDOWS:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.path.join(os.path.expanduser("~"), ".config")
    p = pathlib.Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


CACHE_FILE = data_dir() / "servers_cache.json"
SETTINGS_FILE = data_dir() / "settings.json"
LOG_FILE = data_dir() / "mdavari.log"

DEFAULT_SETTINGS = {
    # --- تست پینگ ---
    "ping_timeout": 2.0,          # ثانیه
    "ping_workers": 64,           # تعداد تست هم‌زمان
    "ping_top": 120,              # حداکثر چند سرور تست شود (۰ = همه)
    # --- اتصال ---
    "connect_timeout": 60,        # ثانیه
    "only_port_443": True,        # ویندوز فقط پورت ۴۴۳ را پشتیبانی می‌کند
    "split_tunneling": False,     # False = کل ترافیک از تونل (پیشنهاد)
    "auto_reconnect": True,
    "connect_on_start": False,
    "auto_ping_after_fetch": True,
    # --- ظاهر ---
    "theme": "dark",              # dark | light
    "log_lines": 400,
    # --- آخرین وضعیت ---
    "last_server": "",
    "cache_max_age": 6 * 3600,    # ثانیه
}


class Settings(dict):
    """دیکشنری تنظیمات با ذخیره‌ی خودکار در فایل JSON."""

    def __init__(self, path: pathlib.Path | None = None):
        super().__init__()
        self.path = pathlib.Path(path) if path else SETTINGS_FILE
        self.update(DEFAULT_SETTINGS)
        self.load()

    # --- I/O -------------------------------------------------------------
    def load(self) -> None:
        try:
            if self.path.exists():
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    for k, v in data.items():
                        self[k] = v
        except Exception:
            pass

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(dict(self), ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def set(self, key: str, value) -> None:
        self[key] = value
        self.save()


def now_str() -> str:
    return time.strftime("%H:%M:%S")


def fa_digits(text) -> str:
    """تبدیل ارقام لاتین به فارسی برای نمایش."""
    table = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return str(text).translate(table)


def human_uptime(seconds: int) -> str:
    seconds = int(max(0, seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
