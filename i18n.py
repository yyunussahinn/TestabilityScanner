"""
i18n.py — Testability Scanner
────────────────────────────────────────────────────────────────
Dil yönetim modülü.

Kullanım:
    from i18n import t, set_lang, get_lang, available_langs

    t("btn_run")                        → "▶  CALISTIR"  (aktif dile göre)
    t("log_platform", platform="iOS")  → format parametresi desteklenir
    set_lang("EN")                      → dili değiştirir (tüm import edenler etkiler)
    get_lang()                          → "TR"
    available_langs()                   → ["TR", "EN"]

Kural:
  - Aktif dilde anahtar yoksa EN'den döner.
  - EN'de de yoksa anahtarın kendisini döner (sessiz fallback).
  - strings.json projeyle aynı klasörde olmalı.
"""

import json
import os
from typing import Callable

_STRINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "strings.json")
_DEFAULT_LANG = "EN"

_strings:    dict[str, dict] = {}
_active_lang: str = "TR"
_listeners:   list[Callable] = []   # dil değişince çağrılacak callback'ler


def _load() -> None:
    global _strings
    try:
        with open(_STRINGS_FILE, "r", encoding="utf-8") as f:
            _strings = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"strings.json bulunamadı: {_STRINGS_FILE}\n"
            "Lütfen strings.json dosyasının uygulama ile aynı klasörde olduğundan emin olun."
        )
    except json.JSONDecodeError as e:
        raise ValueError(f"strings.json parse hatası: {e}")


_load()  # modül import edilince otomatik yükle


# ── Public API ────────────────────────────────────────────────────────────────

def t(key: str, **kwargs) -> str:
    """
    Aktif dilde anahtar karşılığını döner.
    kwargs verilirse .format(**kwargs) uygulanır.

    Öncelik: aktif dil → EN → key (sessiz fallback)
    """
    val = (_strings.get(_active_lang, {}).get(key)
           or _strings.get(_DEFAULT_LANG, {}).get(key)
           or key)
    if kwargs:
        try:
            val = val.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return val


def set_lang(lang: str) -> None:
    """Aktif dili değiştirir ve kayıtlı listener'ları bildirir."""
    global _active_lang
    lang = lang.upper()
    if lang not in _strings:
        raise ValueError(f"Desteklenmeyen dil: '{lang}'. Mevcut: {available_langs()}")
    if lang == _active_lang:
        return
    _active_lang = lang
    for cb in _listeners:
        try:
            cb(lang)
        except Exception:
            pass


def get_lang() -> str:
    """Aktif dil kodunu döner: 'TR', 'EN', vb."""
    return _active_lang


def available_langs() -> list[str]:
    """strings.json'daki tüm dil kodlarını döner."""
    return list(_strings.keys())


def reload() -> None:
    """strings.json'ı diskten yeniden yükler (geliştirme/hot-reload için)."""
    _load()


def on_lang_change(callback: Callable) -> None:
    """
    Dil değiştiğinde çağrılacak fonksiyonu kaydeder.
    callback(new_lang: str) imzasında olmalı.
    """
    if callback not in _listeners:
        _listeners.append(callback)


def remove_listener(callback: Callable) -> None:
    """Kayıtlı listener'ı kaldırır."""
    if callback in _listeners:
        _listeners.remove(callback)