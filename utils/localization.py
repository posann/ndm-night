import json
import os
from utils.helpers import get_resource_path

_translations = {}
_current_lang = "en"

def init_localization(lang=None):
    """Initializes the localization system with the specified language."""
    global _translations, _current_lang
    
    if lang is None:
        lang = "en"
            
    _current_lang = lang
    
    # Use the resource helper for PyInstaller compatibility
    path = get_resource_path(os.path.join("localization", f"{lang}.json"))
    
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                new_translations = json.load(f)
                _translations.clear()
                _translations.update(new_translations)
                # print(f"Successfully loaded localization: {lang} from {path}")
        except Exception as e:
            print(f"Error loading translation file '{path}': {e}")
    else:
        # If the specific language fails, we don't clear translations to keep English defaults
        print(f"CRITICAL: Translation file not found at: {path}")
        # Check current implementation location
        # print(f"Current script location: {__file__}")

def L(key, default=None, **kwargs):
    """
    Localize string using dot notation (e.g., 'sidebar.active').
    Supports kwargs for formatting (e.g., L('stats.active', count=5)).
    """
    parts = key.split('.')
    val = _translations
    for p in parts:
        if isinstance(val, dict) and p in val:
            val = val[p]
        elif isinstance(val, list) and p.isdigit() and int(p) < len(val):
            val = val[int(p)]
        else:
            # Fallback to key or default
            res = default if default is not None else key
            if kwargs:
                try: res = res.format(**kwargs)
                except: pass
            return res
            
    if isinstance(val, str) and kwargs:
        try:
            return val.format(**kwargs)
        except Exception as e:
            print(f"Error formatting string '{key}': {e}")
            return val
            
    return val if val else (default if default is not None else key)

def get_current_lang():
    return _current_lang
