"""موتور اتصال.

ویندوز: SSTP بومی ویندوز (RAS) از طریق PowerShell + rasdial
         → بدون درایور، بدون نصب ابزار جانبی، بدون ادمین (مگر در موارد خاص)
سایر سیستم‌ها: Mock برای تست رابط کاربری
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from . import config
from .sources import Server

CREATE_NO_WINDOW = 0x08000000

# کدهای خطای رایج rasdial → توضیح فارسی
RAS_ERRORS = {
    0: "موفق",
    691: "نام کاربری/رمز عبور رد شد (vpn/vpn)",
    623: "دفترچه تلفن پیدا نشد",
    624: "امکان نوشتن در دفترچه تلفن نیست",
    720: "پروتکل PPP با مشکل مواجه شد؛ سرور را عوض کن",
    739: "سرور RAS در دسترس نیست",
    789: "خطای لایه امنیتی؛ سرور را عوض کن",
    798: "گواهی سرور پیدا نشد",
    800: "سرور در دسترس نیست (احتمال فیلتر بودن یا قطع بودن)",
    809: "سرور جواب نداد (تایم‌اوت)؛ احتمالاً فیلتر است",
    868: "نام سرور resolve نشد (مشکل DNS)",
}


def explain_ras_error(code: int) -> str:
    if code in RAS_ERRORS:
        return f"{RAS_ERRORS[code]} (کد {code})"
    return f"خطای ناشناخته‌ی اتصال (کد {code})"


class BaseEngine:
    def preflight(self) -> tuple[bool, str]:
        return True, ""

    def connect(self, server: Server, split_tunneling: bool = False) -> tuple[bool, str]:
        raise NotImplementedError

    def disconnect(self) -> tuple[bool, str]:
        raise NotImplementedError

    def status(self) -> str:
        """'connected' | 'disconnected' | 'unknown'"""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# ویندوز
# ---------------------------------------------------------------------------
class WindowsSstpEngine(BaseEngine):
    NAME = "MDavariVPN"

    def __init__(self, log: Callable[[str], None] = print):
        self.log = log
        self._current_host: str | None = None
        self._lock = threading.Lock()
        self._ps_exe = self._find_powershell()

    # --- زیرساخت ---------------------------------------------------------
    @staticmethod
    def _find_powershell() -> str:
        for name in ("powershell.exe", "powershell", "pwsh.exe", "pwsh"):
            p = shutil.which(name)
            if p:
                return p
        default = Path(os.environ.get("SystemRoot", r"C:\Windows")) / \
            "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        return str(default)

    def _ps(self, script: str, timeout: float = 120, elevated: bool = False,
            tag: str = "") -> tuple[int, str, str]:
        """اجرای اسکریپت پاورشل به‌صورت مخفی."""
        if elevated:
            return self._ps_elevated(script, timeout, tag)
        try:
            res = subprocess.run(
                [self._ps_exe, "-NoProfile", "-NonInteractive",
                 "-ExecutionPolicy", "Bypass", "-Command", script],
                capture_output=True, text=True, timeout=timeout,
                encoding="utf-8", errors="replace",
                creationflags=CREATE_NO_WINDOW if config.IS_WINDOWS else 0,
            )
            return res.returncode, (res.stdout or "").strip(), (res.stderr or "").strip()
        except subprocess.TimeoutExpired:
            return 124, "", "timeout"
        except FileNotFoundError:
            return 127, "", "powershell not found"
        except Exception as e:  # noqa: BLE001
            return 1, "", str(e)

    def _ps_elevated(self, script: str, timeout: float, tag: str) -> tuple[int, str, str]:
        """اجرا با دسترسی ادمین (یک‌بار پنجره‌ی UAC نمایش داده می‌شود)."""
        tmp_dir = config.data_dir()
        ps1 = tmp_dir / f"elevated_{tag or 'run'}.ps1"
        out = tmp_dir / f"elevated_{tag or 'run'}.out"
        wrapper = (
            "$ErrorActionPreference='Stop'\n"
            "try {\n" + script + "\n}\n"
            "catch { $_ | Out-String | Out-File -Encoding utf8 '{}' }\n"
            "$LASTEXITCODE | Out-File -Append -Encoding utf8 '{}'\n"
        ).format(str(out), str(out))
        ps1.write_text(wrapper, encoding="utf-8-sig")
        if out.exists():
            out.unlink()
        launch = (
            f"Start-Process -FilePath '{self._ps_exe}' -Verb RunAs -Wait "
            f"-ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','{ps1}'"
        )
        try:
            subprocess.run(
                [self._ps_exe, "-NoProfile", "-Command", launch],
                capture_output=True, text=True, timeout=timeout,
                encoding="utf-8", errors="replace",
                creationflags=CREATE_NO_WINDOW if config.IS_WINDOWS else 0,
            )
        except Exception as e:  # noqa: BLE001
            return 1, "", str(e)
        text = out.read_text(encoding="utf-8", errors="replace") if out.exists() else ""
        return (0 if text else 1), text, ""

    @staticmethod
    def _needs_admin(text: str) -> bool:
        low = text.lower()
        return ("access is denied" in low or "access denied" in low
                or "دسترسی" in low or "0x80070005" in low)

    def preflight(self) -> tuple[bool, str]:
        if not config.IS_WINDOWS:
            return False, "این موتور فقط روی ویندوز کار می‌کند"
        rc, out, err = self._ps(
            "$s = Get-Service -Name RasMan -ErrorAction SilentlyContinue; "
            "if ($s) { $s.Status } else { 'missing' }", timeout=25)
        if "Running" not in out:
            return False, "سرویس مدیریت اتصال از راه دور (RasMan) فعال نیست"
        return True, ""

    # --- مدیریت پروفایل ---------------------------------------------------
    def _profile_exists(self) -> bool:
        rc, out, _ = self._ps(
            f"if (Get-VpnConnection -Name '{self.NAME}' -ErrorAction SilentlyContinue)"
            f" {{ 'yes' }} else {{ 'no' }}", timeout=30)
        return "yes" in out.lower()

    def ensure_profile(self, host: str, split_tunneling: bool = False,
                       retries: int = 2) -> tuple[bool, str]:
        """پروفایل SSTP را می‌سازد/به‌روز می‌کند."""
        with self._lock:
            if self._current_host == host and self._profile_exists():
                return True, ""
            split_flag = "-SplitTunneling " if split_tunneling else ""
            script = (
                f"$n='{self.NAME}'\n"
                f"Remove-VpnConnection -Name $n -Force -ErrorAction SilentlyContinue\n"
                f"Add-VpnConnection -Name $n -ServerAddress '{host}' -TunnelType Sstp "
                f"-EncryptionLevel Required -AuthenticationMethod MSChapv2 "
                f"{split_flag}-RememberCredential -Force -ErrorAction Stop | Out-Null\n"
                f"if (Get-VpnConnection -Name $n -ErrorAction SilentlyContinue) "
                f"{{ 'PROFILE-OK' }} else {{ 'PROFILE-MISSING' }}"
            )
            rc, out, err = self._ps(script, timeout=90)
            if "PROFILE-OK" in out:
                self._current_host = host
                return True, ""
            combined = f"{out} {err}"
            if self._needs_admin(combined) or rc not in (0,):
                self.log("[UAC] برای ساخت پروفایل نیاز به دسترسی ادمین است؛ پنجره‌ی UAC را تأیید کن…")
                rc2, out2, err2 = self._ps(script + "\n'PROFILE-OK'", timeout=180,
                                           elevated=True, tag="profile")
                if "PROFILE-OK" in out2:
                    self._current_host = host
                    return True, ""
                combined = f"{out2} {err2}"
            return False, f"ساخت پروفایل ناموفق بود: {combined.strip()[:300]}"

    def remove_profile(self) -> None:
        self._ps(f"Remove-VpnConnection -Name '{self.NAME}' -Force "
                 f"-ErrorAction SilentlyContinue", timeout=45)
        self._current_host = None

    # --- اتصال ------------------------------------------------------------
    def connect(self, server: Server, split_tunneling: bool = False) -> tuple[bool, str]:
        if server.port != 443:
            return False, (f"ویندوز فقط پورت ۴۴۳ را برای SSTP پشتیبانی می‌کند "
                           f"(این سرور پورت {server.port} دارد)")
        ok, msg = self.ensure_profile(server.host, split_tunneling)
        if not ok:
            return False, msg
        self.log(f"- در حال اتصال به {server.label} …")
        rc, out, err = self._ps(
            f'rasdial "{self.NAME}" vpn vpn', timeout=120)
        text = f"{out}\n{err}"
        if rc == 0 and ("successfully" in text.lower() or self.status() == "connected"):
            return True, "متصل شد"
        # برخی کدها داخل متن خروجی برمی‌گردند
        m = re.search(r"\b(6\d\d|7\d\d|8\d\d)\b", text)
        code = int(m.group(1)) if m else rc
        return False, explain_ras_error(code)

    def disconnect(self) -> tuple[bool, str]:
        self._ps(f'rasdial "{self.NAME}" /disconnect', timeout=60)
        state = self.status()
        return state != "connected", "" if state != "connected" else "قطع نشد"

    def status(self) -> str:
        """چک سریع: اگر آداپتور PPP با نام پروفایل در ipconfig باشد یعنی وصل است."""
        if not config.IS_WINDOWS:
            return "unknown"
        try:
            res = subprocess.run(
                ["ipconfig"], capture_output=True, text=True, timeout=12,
                encoding="utf-8", errors="replace", creationflags=CREATE_NO_WINDOW)
            text = res.stdout or ""
            if not text.strip():
                # بعضی ویندوزها خروجی را در کدپیج محلی می‌دهند
                res = subprocess.run(["ipconfig"], capture_output=True, timeout=12,
                                     creationflags=CREATE_NO_WINDOW)
                text = (res.stdout or b"").decode("mbcs", "replace")
            if self.NAME in text:
                return "connected"
            return "disconnected"
        except Exception:
            pass
        # مسیر پشتیبان: PowerShell (کندتر، ولی دقیق)
        rc, out, _ = self._ps(
            f"$c = Get-VpnConnection -Name '{self.NAME}' -ErrorAction SilentlyContinue; "
            f"if ($c) {{ $c.ConnectionStatus }} else {{ 'Missing' }}", timeout=30)
        out = out.strip().lower()
        if out.startswith("connected"):
            return "connected"
        if "connecting" in out:
            return "connecting"
        if "disconnected" in out or "missing" in out:
            return "disconnected"
        return "unknown"

    def connection_info(self) -> dict:
        rc, out, _ = self._ps(
            f"$c = Get-VpnConnection -Name '{self.NAME}' -ErrorAction SilentlyContinue; "
            f"if ($c) {{ '{{0}}|{{1}}' -f $c.ServerAddress, $c.ConnectionStatus }}",
            timeout=30)
        if "|" in out:
            host, state = out.split("|", 1)
            return {"server": host.strip(), "state": state.strip()}
        return {}


# ---------------------------------------------------------------------------
# Mock (برای تست رابط کاربری روی غیر ویندوز)
# ---------------------------------------------------------------------------
class MockEngine(BaseEngine):
    def __init__(self, log: Callable[[str], None] = print):
        self.log = log
        self._connected = False
        self._server: Server | None = None

    def connect(self, server: Server, split_tunneling: bool = False) -> tuple[bool, str]:
        self.log(f"[TEST] (حالت آزمایشی) اتصال به {server.label} …")
        time.sleep(1.2)
        self._connected = True
        self._server = server
        return True, "متصل شد (آزمایشی)"

    def disconnect(self) -> tuple[bool, str]:
        time.sleep(0.4)
        self._connected = False
        return True, ""

    def status(self) -> str:
        return "connected" if self._connected else "disconnected"


def build_engine(log: Callable[[str], None] = print) -> BaseEngine:
    return WindowsSstpEngine(log) if config.IS_WINDOWS else MockEngine(log)
