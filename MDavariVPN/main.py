#!/usr/bin/env python3
"""MDavari VPN PRO — Smart SSTP Client (نسخه ۲)

اجرای عادی:      python main.py
خودآزمایی متنی:  python main.py --selftest
اتصال بدون رابط: python main.py --connect-best
اسکرین‌شات (لینوکس): python main.py --screenshot out.png
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import config  # noqa: E402


def selftest() -> int:
    from app import pinger, sources
    from app.engine import build_engine
    print(f"MDavari VPN v{config.VERSION}  ({sys.platform})")
    print(f"پوشه‌ی داده: {config.data_dir()}")
    engine = build_engine(print)
    ok, msg = engine.preflight()
    print(f"موتور اتصال: {'آماده' if ok else 'هشدار'} {msg}")
    servers, report = sources.refresh(print, use_headless=config.IS_WINDOWS)
    print(f"منابع: {report}  |  مجموع: {len(servers)}")
    if servers:
        pinger.ping_servers(servers, timeout=2.0, workers=64, limit=30)
        alive = [s for s in servers if s.alive]
        print(f"پینگ: {len(alive)} سرور فعال از ۳۰ سرور اول")
        for s in alive[:10]:
            print(f"   {s.label:42s} {s.country:20s} {s.latency:6.0f} ms")
    print("آی‌پی فعلی:", pinger.get_public_ip())
    print("✅ خودآزمایی تمام شد")
    return 0


def connect_best() -> int:
    import time
    from app import pinger, sources
    from app.engine import build_engine
    s = config.Settings()
    engine = build_engine(print)
    servers, _ = sources.refresh(print, only_port_443=bool(s.get("only_port_443")))
    pinger.ping_servers(servers, timeout=2.0, workers=64, limit=s.get("ping_top") or None)
    alive = [x for x in servers if x.alive and x.port == 443]
    alive.sort(key=lambda x: x.latency or 9e9)
    for srv in alive[:5]:
        ok, msg = engine.connect(srv, split_tunneling=bool(s.get("split_tunneling")))
        print(("✅ " if ok else "⚠️ ") + f"{srv.label}: {msg}")
        if ok:
            print("وضعیت:", engine.status())
            return 0
        time.sleep(1)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="MDavari VPN")
    parser.add_argument("--selftest", action="store_true", help="خودآزمایی بدون رابط گرافیکی")
    parser.add_argument("--connect-best", action="store_true", help="اتصال به سریع‌ترین سرور")
    parser.add_argument("--screenshot", metavar="PATH", help="گرفتن تصویر از پنجره و خروج")
    parser.add_argument("--ui-smoke", action="store_true", help="تست سریع رابط و خروج")
    parser.add_argument("--page", default="home", help="صفحه‌ی موردنظر برای اسکرین‌شات")
    parser.add_argument("--demo", action="store_true", help="نمایش حالت «متصل» برای اسکرین‌شات")
    parser.add_argument("--delay", type=int, default=5, help="تأخیر اسکرین‌شات (ثانیه)")
    args = parser.parse_args()

    if args.selftest:
        return selftest()
    if args.connect_best:
        return connect_best()

    from app.ui.app import App
    app = App()

    if args.page and args.page != "home":
        app.show_page(args.page)

    if args.demo:
        import time as _t
        from app.sources import Server as _Srv

        def _demo_connect():
            # فقط برای اسکرین‌شات: بدون تغییر فایل تنظیمات کاربر
            app.controller.s["auto_reconnect"] = False
            srv = _Srv(host="public-vpn-223.opengw.net", country="Japan", ping_ms=14,
                       latency=13.0, alive=True, source="demo")
            app.controller.connected_server = srv
            app.controller.connected_at = _t.time()
            app.controller.public_ip = "95.64.48.130"
            app._apply_state({"state": "connected", "server": srv})
            app._update_ip("95.64.48.130")
        app.after(2500, _demo_connect)

    if args.screenshot:
        def shot():
            try:
                app.update()
                os.system(f"import -window root {args.screenshot}")
            except Exception as e:  # noqa: BLE001
                print("screenshot failed:", e)
            app.destroy()
        app.after(max(1, args.delay) * 1000, shot)
        app.mainloop()
        return 0

    if args.ui_smoke:
        for page in ("home", "servers", "shop", "settings"):
            app.show_page(page)
            app.update()
        app.update()
        app.destroy()
        print("✅ رابط کاربری بدون خطا ساخته شد")
        return 0

    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
