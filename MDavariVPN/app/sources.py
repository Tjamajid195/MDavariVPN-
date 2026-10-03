"""گرفتن لیست سرورهای SSTP از چند منبع (چندلایه و مقاوم).

ترتیب تلاش:
  1) خود سایت ipspeed.info با هدرهای مرورگر واقعی
  2) همان سایت از طریق پروکسی خواندنی (r.jina.ai)
  3) مرورگر هدلس Edge (فقط ویندوز) برای رد شدن از Cloudflare
  4) API رسمی VPN Gate
  5) مخازن گیت‌هاب که همین لیست SSTP را به‌روز نگه می‌دارند
  6) کش محلی (همیشه به‌عنوان تور نجات)
"""
from __future__ import annotations

import gzip
import io
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from typing import Callable, Iterable, Optional

from . import config

# --------------------------------------------------------------------------
# منابع
# --------------------------------------------------------------------------
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
BROWSER_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,fa;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "sec-ch-ua": '"Chromium";v="126", "Not:A-Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
    "Connection": "keep-alive",
}

IPSIP_SITE_URLS = [
    "https://ipspeed.info/free-sstp.php",
    "https://m.ipspeed.info/freevpn_sstp.php?language=en",
]
JINA_PREFIX = "https://r.jina.ai/"
VPNGATE_API = "https://www.vpngate.net/api/iphone/"
MIRROR_URLS = [
    "https://raw.githubusercontent.com/Koros0111/Vpn-Gate-SSTP/main/sstp_hosts.txt",
    "https://raw.githubusercontent.com/Delta-Kronecker/Vpn-Gate/main/sstp_hosts.txt",
]

# --------------------------------------------------------------------------
# الگوهای تشخیص
# --------------------------------------------------------------------------
HOST_RE = re.compile(r"([A-Za-z0-9][A-Za-z0-9\.\-]*\.opengw\.net)(?::(\d{1,5}))?")
PING_RE = re.compile(r"([\d,]{1,7})\s*ms\b", re.I)
UPTIME_RE = re.compile(
    r"(\d{1,4})\s*(mins?|minutes?|hours?|days?|ساعت|دقیقه|روز|روز پیش|ثانیه)", re.I
)
TAG_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.I | re.S)
ANYTAG_RE = re.compile(r"<[^>]+>")
ENTITIES = [
    ("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
    ("&quot;", '"'), ("&#039;", "'"), ("&zwnj;", "\u200c"),
]

COUNTRIES: list[tuple[str, list[str]]] = [
    ("Japan", ["japan", "ژاپن", "tokyo"]),
    ("Republic of Korea", ["korea", "کره", "seoul"]),
    ("Thailand", ["thailand", "تایلند"]),
    ("Russian Federation", ["russia", "روس", "moscow"]),
    ("Vietnam", ["viet nam", "vietnam", "ویتنام", "viet"]),
    ("United States", ["united states", "america", "آمریکا", "usa", "los angeles"]),
    ("Brazil", ["brazil", "برزیل"]),
    ("Iran", ["iran", "ایران", "تهران", "tehran"]),
    ("Ukraine", ["ukraine", "اوکراین"]),
    ("Kazakhstan", ["kazakhstan", "قزاقستان"]),
    ("Indonesia", ["indonesia", "اندونزی"]),
    ("Taiwan", ["taiwan", "تایوان"]),
    ("Hong Kong", ["hong kong", "هنگ کنگ"]),
    ("India", ["india", "هند"]),
    ("Turkey", ["turkey", "ترکیه"]),
    ("France", ["france", "فرانسه"]),
    ("Germany", ["germany", "آلمان"]),
    ("United Kingdom", ["united kingdom", "england", "انگلیس", "london"]),
    ("Netherlands", ["netherlands", "هلند"]),
    ("Canada", ["canada", "کانادا"]),
    ("Singapore", ["singapore", "سنگاپور"]),
    ("Romania", ["romania", "رومانی"]),
    ("Moldova", ["moldova", "مولداوی"]),
    ("Bulgaria", ["bulgaria", "بلغارستان"]),
    ("Poland", ["poland", "لهستان"]),
    ("China", ["china", "چین"]),
]
SHORT_CODE_RE = re.compile(r"\b(US|JP|KR|TH|RU|VN|BR|IR|UA|KZ|ID|TW|HK|IN|TR|FR|DE|GB|UK|NL|CA|SG|RO|MD|BG|PL|CN)\b")

COUNTRY_FA = {
    "Japan": "ژاپن", "Republic of Korea": "کره جنوبی", "Thailand": "تایلند",
    "Russian Federation": "روسیه", "Vietnam": "ویتنام", "United States": "آمریکا",
    "Brazil": "برزیل", "Iran": "ایران", "Ukraine": "اوکراین", "Kazakhstan": "قزاقستان",
    "Indonesia": "اندونزی", "Taiwan": "تایوان", "Hong Kong": "هنگ‌کنگ", "India": "هند",
    "Turkey": "ترکیه", "France": "فرانسه", "Germany": "آلمان",
    "United Kingdom": "انگلستان", "Netherlands": "هلند", "Canada": "کانادا",
    "Singapore": "سنگاپور", "Romania": "رومانی", "Moldova": "مولداوی",
    "Bulgaria": "بلغارستان", "Poland": "لهستان", "China": "چین", "Unknown": "نامشخص",
}


@dataclass
class Server:
    host: str
    port: int = 443
    country: str = ""
    ping_ms: int | None = None     # پینگ اعلام‌شده توسط منبع
    uptime: str = ""
    source: str = ""
    latency: float | None = None   # پینگ واقعی اندازه‌گیری‌شده توسط ما
    alive: bool | None = None

    @property
    def key(self) -> str:
        return f"{self.host}:{self.port}"

    @property
    def label(self) -> str:
        return self.host if self.port == 443 else f"{self.host}:{self.port}"

    @property
    def country_fa(self) -> str:
        return COUNTRY_FA.get(self.country or "Unknown", self.country or "نامشخص")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Server":
        allowed = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**allowed)


# --------------------------------------------------------------------------
# ابزارهای متن و HTTP
# --------------------------------------------------------------------------
def strip_tags(chunk: str) -> str:
    chunk = TAG_RE.sub(" ", chunk)
    chunk = ANYTAG_RE.sub(" ", chunk)
    for a, b in ENTITIES:
        chunk = chunk.replace(a, b)
    return re.sub(r"\s+", " ", chunk).strip()


def looks_like_challenge(text: str) -> bool:
    head = text[:6000].lower()
    return (
        "just a moment" in head
        or "cf-mitigated" in head
        or "cf-chl" in head
        or "enable javascript and cookies" in head
    )


def http_get(url: str, timeout: float = 20.0, headers: dict | None = None,
             use_system_proxy: bool = True):
    """درخواست GET ساده با urllib (بدون وابستگی بیرونی)."""
    hdrs = dict(BROWSER_HEADERS)
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    handlers = []
    if not use_system_proxy:
        handlers.append(urllib.request.ProxyHandler({}))
    opener = urllib.request.build_opener(*handlers)
    try:
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read()
            if resp.headers.get("Content-Encoding", "").lower() == "gzip":
                raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
            return resp.status, raw.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            body = ""
        return e.code, body
    except Exception as e:  # noqa: BLE001
        return 0, f"__ERROR__ {e}"


def detect_country(row_text: str) -> str:
    low = row_text.lower()
    for name, keys in COUNTRIES:
        for k in keys:
            if k in low:
                return name
    m = SHORT_CODE_RE.search(row_text)
    if m:
        code = m.group(1)
        mapping = {
            "US": "United States", "JP": "Japan", "KR": "Republic of Korea",
            "TH": "Thailand", "RU": "Russian Federation", "VN": "Vietnam",
            "BR": "Brazil", "IR": "Iran", "UA": "Ukraine", "KZ": "Kazakhstan",
            "ID": "Indonesia", "TW": "Taiwan", "HK": "Hong Kong", "IN": "India",
            "TR": "Turkey", "FR": "France", "DE": "Germany",
            "GB": "United Kingdom", "UK": "United Kingdom", "NL": "Netherlands",
            "CA": "Canada", "SG": "Singapore", "RO": "Romania", "MD": "Moldova",
            "BG": "Bulgaria", "PL": "Poland", "CN": "China",
        }
        return mapping.get(code, "")
    return ""


def _normalize_country(raw: str) -> str:
    """«Croatia (LOCAL Name: Hrvatska)» → «Croatia» و اصلاح نام کره."""
    c = re.sub(r"\(.*?\)", "", raw or "").strip()
    c = re.sub(r"\s{2,}", " ", c)
    if c.lower().startswith("korea republic"):
        return "Republic of Korea"
    return c


def iter_rows(text: str) -> Iterable[str]:
    """متن را به ردیف‌های قابل تحلیل تبدیل می‌کند (HTML یا متن ساده)."""
    if "<tr" in text.lower() or "<table" in text.lower():
        body = re.sub(r"</tr>", "\n", text, flags=re.I)
        for chunk in body.splitlines():
            row = strip_tags(chunk)
            if row:
                yield row
    else:
        for line in text.splitlines():
            row = line.strip()
            if row:
                yield row


def parse_servers(text: str, source: str) -> list[Server]:
    out: list[Server] = []
    for row in iter_rows(text):
        for m in HOST_RE.finditer(row):
            host = m.group(1)
            port = int(m.group(2)) if m.group(2) else 443
            if not (1 <= port <= 65535):
                port = 443
            ping_m = PING_RE.search(row)
            up_m = UPTIME_RE.search(row)
            out.append(
                Server(
                    host=host,
                    port=port,
                    country=detect_country(row),
                    ping_ms=int(ping_m.group(1).replace(",", "")) if ping_m else None,
                    uptime=up_m.group(0) if up_m else "",
                    source=source,
                )
            )
        # حالت تک‌خطی مثل mirror ها: host:port بدون کلمه‌ی اضافه
    return out


# --------------------------------------------------------------------------
# منابع جداگانه
# --------------------------------------------------------------------------
def fetch_ipspeed_direct(log: Callable[[str], None]) -> tuple[list[Server], str]:
    for url in IPSIP_SITE_URLS:
        status, text = http_get(url, timeout=25)
        if status == 200 and not looks_like_challenge(text):
            servers = parse_servers(text, "ipspeed.info")
            if servers:
                log(f"✓ لیست از خود سایت گرفته شد ({len(servers)} سرور) — {url}")
                return servers, url
            log(f"! صفحه‌ی سایت باز شد ولی سروری داخلش پیدا نشد — {url}")
        elif looks_like_challenge(text):
            log(f"[CF] Cloudflare جلوی درخواست ساده را گرفت (challenge) — {url}")
        else:
            log(f"! پاسخ ناموفق از سایت: کد {status} — {url}")
    return [], ""


def fetch_ipspeed_jina(log: Callable[[str], None]) -> tuple[list[Server], str]:
    for url in IPSIP_SITE_URLS:
        status, text = http_get(JINA_PREFIX + url, timeout=40)
        if status == 200 and not looks_like_challenge(text):
            servers = parse_servers(text, "ipspeed.info(jina)")
            if servers:
                log(f"✓ لیست از سایت (مسیر جایگزین) گرفته شد ({len(servers)} سرور)")
                return servers, url
        else:
            log("! مسیر جایگزین هم جواب نداد")
    return [], ""


def find_edge() -> str | None:
    if not config.IS_WINDOWS:
        return None
    candidates = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


def fetch_via_headless_browser(log: Callable[[str], None]) -> tuple[list[Server], str]:
    """اجرای Edge/Chrome هدلس و خواندن DOM بعد از عبور از چالش Cloudflare."""
    exe = find_edge()
    if not exe:
        log("i مرورگر Edge/Chrome پیدا نشد؛ از این مسیر صرف‌نظر می‌کنیم")
        return [], ""
    profile = config.data_dir() / "browser_profile"
    profile.mkdir(parents=True, exist_ok=True)
    for mode in ("--headless=new", "--headless"):
        for url in IPSIP_SITE_URLS:
            cmd = [
                exe, mode, "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                "--disable-extensions", "--mute-audio", "--hide-scrollbars",
                f"--user-data-dir={profile}", "--virtual-time-budget=20000",
                "--dump-dom", url,
            ]
            try:
                kwargs = {}
                if config.IS_WINDOWS:
                    kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=90,
                                     encoding="utf-8", errors="replace", **kwargs)
                html = res.stdout or ""
            except Exception as e:  # noqa: BLE001
                log(f"! اجرای مرورگر هدلس ناموفق بود: {e}")
                continue
            if html and not looks_like_challenge(html):
                servers = parse_servers(html, "ipspeed.info(browser)")
                if servers:
                    log(f"✓ با مرورگر هدلس چالش رد شد ({len(servers)} سرور)")
                    return servers, url
            else:
                log("[CF] مرورگر هدلس هم چالش را رد نکرد (profile را یک‌بار دستی باز کن)")
    return [], ""


def fetch_vpngate(log: Callable[[str], None]) -> tuple[list[Server], str]:
    status, text = http_get(VPNGATE_API, timeout=25)
    if status != 200 or text.startswith("__ERROR__"):
        log(f"! API ونگیت جواب نداد (کد {status})")
        return [], ""
    out: list[Server] = []
    for line in text.splitlines():
        if not line or line.startswith("*") or line.startswith("#"):
            continue
        parts = line.split(",")
        if len(parts) < 6:
            continue
        host = parts[0].strip()
        if not host:
            continue
        if "." not in host:
            host = host + ".opengw.net"
        try:
            ping = int(float(parts[3]))
        except Exception:
            ping = None
        country = _normalize_country(parts[5])
        out.append(Server(host=host, port=443, country=country, ping_ms=ping,
                          source="vpngate-api"))
    if out:
        log(f"✓ منبع پشتیبان VPN Gate: {len(out)} سرور")
    return out, VPNGATE_API


def fetch_mirrors(log: Callable[[str], None]) -> tuple[list[Server], str]:
    out: list[Server] = []
    used = ""
    for url in MIRROR_URLS:
        status, text = http_get(url, timeout=20)
        if status != 200 or "__ERROR__" in text:
            continue
        cnt = 0
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = re.search(r"([A-Za-z0-9\.\-]+\.opengw\.net)(?::(\d{1,5}))?", line)
            if not m:
                continue
            out.append(Server(
                host=m.group(1),
                port=int(m.group(2)) if m.group(2) else 443,
                country=detect_country(line),
                source="github-mirror",
            ))
            cnt += 1
        if cnt:
            used = url
            log(f"✓ آینه‌ی گیت‌هاب: {cnt} آدرس")
            break
    return out, used


def geo_fill(servers: list[Server], log: Callable[[str], None],
             limit: int = 100) -> None:
    """کشوردهی به سرورهای بی‌کشور با ip-api.com (اختیاری، خطا نادیده گرفته می‌شود)."""
    todo = [s for s in servers if not s.country][:limit]
    if not todo:
        return
    try:
        ips: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=32) as ex:
            futs = {ex.submit(_resolve, s.host): s for s in todo}
            for fut in futs:
                s = futs[fut]
                ip = fut.result()
                if ip:
                    ips[s.host] = ip
        if not ips:
            return
        payload = json.dumps([{"query": ip} for ip in set(ips.values())]).encode()
        req = urllib.request.Request(
            "http://ip-api.com/batch?fields=query,country",
            data=payload, headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        ip2c = {d.get("query"): d.get("country", "") for d in data if isinstance(d, dict)}
        filled = 0
        for s in todo:
            c = ip2c.get(ips.get(s.host, ""), "")
            if c:
                s.country = c
                filled += 1
        if filled:
            log(f"@ کشور {filled} سرور تکمیل شد")
    except Exception:
        return


def _resolve(host: str) -> str | None:
    try:
        return socket.gethostbyname(host)
    except Exception:
        return None


# --------------------------------------------------------------------------
# ادغام، کش و تابع اصلی
# --------------------------------------------------------------------------
def merge(*lists: Iterable[Server]) -> list[Server]:
    merged: dict[str, Server] = {}
    for lst in lists:
        for s in lst:
            cur = merged.get(s.key)
            if cur is None:
                merged[s.key] = s
            else:
                if not cur.country and s.country:
                    cur.country = s.country
                if cur.ping_ms is None and s.ping_ms is not None:
                    cur.ping_ms = s.ping_ms
                if not cur.uptime and s.uptime:
                    cur.uptime = s.uptime
                if s.source and s.source not in (cur.source or ""):
                    cur.source = (cur.source + "+" + s.source).strip("+")
    return list(merged.values())


def save_cache(servers: list[Server]) -> None:
    try:
        config.CACHE_FILE.write_text(
            json.dumps(
                {"time": time.time(), "servers": [s.to_dict() for s in servers]},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass


def load_cache(max_age: float | None = None) -> list[Server]:
    try:
        if not config.CACHE_FILE.exists():
            return []
        data = json.loads(config.CACHE_FILE.read_text(encoding="utf-8"))
        if max_age is not None and time.time() - float(data.get("time", 0)) > max_age:
            return []
        return [Server.from_dict(d) for d in data.get("servers", [])]
    except Exception:
        return []


def refresh(log: Callable[[str], None] = print, only_port_443: bool = False,
            use_headless: bool = True, do_geo: bool = True) -> tuple[list[Server], dict]:
    """لیست سرورها را از همه‌ی منابع موجود جمع می‌کند."""
    log("… شروع دریافت لیست سرورها…")
    collected: list[list[Server]] = []
    report: dict[str, int] = {}

    tries = [
        ("site", lambda: fetch_ipspeed_direct(log)),
        ("site-alt", lambda: fetch_ipspeed_jina(log)),
    ]
    if use_headless and config.IS_WINDOWS:
        tries.append(("browser", lambda: fetch_via_headless_browser(log)))
    tries += [
        ("vpngate", lambda: fetch_vpngate(log)),
        ("mirror", lambda: fetch_mirrors(log)),
    ]

    for name, fn in tries:
        try:
            servers, _ = fn()
        except Exception as e:  # noqa: BLE001
            log(f"! منبع «{name}» خطا داد: {e}")
            servers = []
        if servers:
            report[name] = len(servers)
            collected.append(servers)

    servers = merge(*collected)
    if not servers:
        cached = load_cache()
        if cached:
            log(f"~ از لیست ذخیره‌شده‌ی قبلی استفاده می‌کنیم ({len(cached)} سرور)")
            return _finalize(cached, only_port_443), {"cache": len(cached)}
        log("✗ هیچ منبعی جواب نداد و کش هم خالی است")
        return [], {}

    if do_geo:
        geo_fill(servers, log)

    servers.sort(key=lambda s: (s.ping_ms is None, s.ping_ms or 99999))
    save_cache(servers)
    log(f"# مجموع: {len(servers)} سرور یکتا از {len(report)} منبع")
    return _finalize(servers, only_port_443), report


def _finalize(servers: list[Server], only_port_443: bool) -> list[Server]:
    if only_port_443:
        servers = [s for s in servers if s.port == 443]
    return servers
