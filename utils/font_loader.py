"""
Font loader utility for NDM.
Loads Poppins TTF files into the Windows GDI font registry so
customtkinter (and tkinter) can use ("Poppins", size) tuples directly.
"""

import os
import ctypes
import sys
from utils.helpers import get_resource_path

# Windows GDI constant: load as a private, per-process font
FR_PRIVATE = 0x10

_fonts_loaded = False


def load_poppins(fonts_dir: str | None = None) -> bool:
    """
    Register all Poppins TTF files in *fonts_dir* with the GDI.
    Returns True if at least one font was loaded.
    Call this ONCE before creating any tkinter widgets.
    """
    global _fonts_loaded
    if _fonts_loaded:
        return True

    if fonts_dir is None:
        # Resolve path via resource helper for PyInstaller compatibility
        fonts_dir = get_resource_path("fonts")

    if not os.path.isdir(fonts_dir):
        return False

    try:
        gdi32 = ctypes.windll.gdi32
    except AttributeError:
        # Non-Windows platform – skip gracefully
        return False

    loaded = 0
    for fname in os.listdir(fonts_dir):
        if fname.lower().startswith("poppins") and fname.lower().endswith(".ttf"):
            path = os.path.join(fonts_dir, fname)
            result = gdi32.AddFontResourceExW(path, FR_PRIVATE, 0)
            if result:
                loaded += 1

    _fonts_loaded = loaded > 0
    return _fonts_loaded


def get_font(size: int = 13, weight: str = "normal") -> tuple:
    """
    Return a (family, size, weight) tuple.
    Uses Poppins if loaded, falls back to Segoe UI then Arial.
    """
    family = "Poppins" if _fonts_loaded else "Segoe UI"
    if weight == "bold":
        return (family, size, "bold")
    return (family, size)


# Convenience size presets
def F(size: int, bold: bool = True) -> tuple:
    """Shorthand: F(14) → ('Poppins', 14, 'bold')  |  F(14, False) → ('Poppins', 14)"""
    if bold:
        return get_font(size, "bold")
    return get_font(size)
