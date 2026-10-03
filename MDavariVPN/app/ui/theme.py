"""تم، رنگ‌ها و فونت‌های برنامه."""
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont

DARK = {
    "bg": "#0a0e17",
    "bg2": "#0d1320",
    "card": "#121a2a",
    "card2": "#182236",
    "border": "#22304a",
    "text": "#e9eef8",
    "muted": "#8c9ab4",
    "accent": "#f5a623",
    "accent2": "#ffc061",
    "accent_dim": "#6b4a12",
    "green": "#2ecc71",
    "green_dark": "#0f3d24",
    "red": "#e74c3c",
    "blue": "#3aa0d8",
    "nav": "#101827",
    "shadow": "#0f1727",
    "log_bg": "#080c14",
}

LIGHT = {
    "bg": "#f2f5fa",
    "bg2": "#e8edf6",
    "card": "#ffffff",
    "card2": "#f4f7fc",
    "border": "#d3dcea",
    "text": "#131a26",
    "muted": "#5d6b82",
    "accent": "#e08a00",
    "accent2": "#f5a623",
    "accent_dim": "#f7e2bd",
    "green": "#18a05a",
    "green_dark": "#d5f2e2",
    "red": "#d63b2c",
    "blue": "#1f7fc0",
    "nav": "#ffffff",
    "shadow": "#dfe6f1",
    "log_bg": "#0d1420",
}

PALETTES = {"dark": DARK, "light": LIGHT}

FAVORITE_FONTS = ["Tahoma", "Segoe UI", "Vazirmatn", "Vazir", "IRANSans",
                  "Arial", "DejaVu Sans", "Noto Sans Arabic"]


class Theme:
    def __init__(self, mode: str = "dark"):
        self.mode = mode if mode in PALETTES else "dark"
        self._font_family: str | None = None

    # --- رنگ ---------------------------------------------------------------
    @property
    def colors(self) -> dict:
        return PALETTES[self.mode]

    def c(self, key: str) -> str:
        return self.colors.get(key, "#ff00ff")

    def toggle(self) -> str:
        self.mode = "light" if self.mode == "dark" else "dark"
        return self.mode

    # --- فونت --------------------------------------------------------------
    def font_family(self) -> str:
        if self._font_family is None:
            try:
                families = set(tkfont.families())
            except Exception:
                families = set()
            for f in FAVORITE_FONTS:
                if f in families:
                    self._font_family = f
                    break
            else:
                self._font_family = "TkDefaultFont"
        return self._font_family

    def font(self, size: int = 11, bold: bool = False):
        return (self.font_family(), size, "bold") if bold else (self.font_family(), size)
