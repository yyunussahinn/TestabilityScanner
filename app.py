"""
Where is My Id — GUI  v4.4
──────────────────────────────────────────────────────────────
v4.4 eklemeleri:
  - 3. tab: "📱 Session Tarama" (multi-page, tek driver oturumu)
  - SessionTab mantık sınıfı: session_tab.py
  - _set_session_state() — session durumuna göre buton yönetimi
  - i18n: dil seçimi (TR/EN) header dropdown — strings.json üzerinden yönetilir
"""

import customtkinter as ctk
from smart_tab import SmartTab
from session_tab import SessionTab
from i18n import t, set_lang, get_lang, available_langs, on_lang_change
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import subprocess, threading, sys, os, json
from datetime import datetime

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Palet ────────────────────────────────────────────────────────────────────
ACCENT        = "#000000"
ACCENT_DK     = "#D4A820"
ACCENT_IOS    = "#185FA5"
ACCENT_IOS_DK = "#0C447C"
ACCENT_SES    = "#2D6A2D"
ACCENT_SES_DK = "#1a5220"
BG_MAIN       = "#F5F0E8"
BG_PANEL      = "#FFFFFF"
BG_CARD       = "#F5F0E8"
BG_INPUT      = "#EDE8DF"
T_PRI         = "#2C2416"
T_MUT         = "#8C7D6A"
C_OK          = "#2D6A2D"
C_ERR         = "#A32020"
C_WRN         = "#8C6A10"
C_INF         = "#185FA5"

# ── Fontlar ──────────────────────────────────────────────────────────────────
FT  = ("Courier New", 18, "bold")
FL  = ("Courier New", 11, "bold")
FS  = ("Courier New", 10)
FLG = ("Courier New", 10)
FB  = ("Courier New",  9, "bold")

_BASE       = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(_BASE, "gui_config.json")

# ── Varsayılan profil verileri ────────────────────────────────────────────────
_D_IOS = {
    "device_name": "iPhone 16", "platform_version": "18.6",
    "bundle_id":   "test.com.hitit.pia",
    "udid":        "AD21A917-5271-4DF1-8C5D-E64A0DE8EAD9",
}
_D_AND = {
    "device_name":  "ce04171418dee0010c", "platform_version": "9",
    "app_package":  "test.com.piac.thepiaapp.android",
    "app_activity": "com.piamobile.MainActivity",
}
DEFAULT_CFG = {
    "platform": "ios",
    "language": "TR",
    "output_word": True, "output_excel": True, "output_json": False,
    "output_dir": "", "appium_server": "http://127.0.0.1:4723",
    "document_sections": ["unique", "undefined", "duplicate", "missing"],
    "blacklist_ids": ["statusBarBackground","content","action_bar_root","navigationBarBackground"],
    "ios_profiles":           {"PIA iOS":     _D_IOS.copy()},
    "android_profiles":       {"PIA Android": _D_AND.copy()},
    "active_ios_profile":     "PIA iOS",
    "active_android_profile": "PIA Android",
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg = {**DEFAULT_CFG, **data}
            if "output_format" in cfg and "output_word" not in cfg:
                fmt = cfg["output_format"]
                cfg["output_word"]  = "word"  in fmt
                cfg["output_excel"] = "excel" in fmt
                cfg["output_json"]  = "json"  in fmt
            cfg.setdefault("ios_profiles",     {"PIA iOS":     _D_IOS.copy()})
            cfg.setdefault("android_profiles", {"PIA Android": _D_AND.copy()})
            cfg.setdefault("language", "TR")
            return cfg
        except Exception:
            pass
    return json.loads(json.dumps(DEFAULT_CFG))


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def _build_output_format(cfg) -> str:
    parts = []
    if cfg.get("output_word"):  parts.append("word")
    if cfg.get("output_excel"): parts.append("excel")
    if cfg.get("output_json"):  parts.append("json")
    return "+".join(parts) if parts else "word"


def write_config_py(cfg, path):
    platform = cfg["platform"]
    if platform == "ios":
        pname = cfg.get("active_ios_profile", "")
        p = cfg["ios_profiles"].get(pname, _D_IOS)
        plat = (
            'IOS = {\n'
            f'    "device_name":      "{p["device_name"]}",\n'
            f'    "platform_version": "{p["platform_version"]}",\n'
            f'    "bundle_id":        "{p["bundle_id"]}",\n'
            f'    "udid":             "{p["udid"]}",\n'
            '    "no_reset":         True,\n}\nANDROID = {}\n'
        )
    else:
        pname = cfg.get("active_android_profile", "")
        p = cfg["android_profiles"].get(pname, _D_AND)
        plat = (
            'ANDROID = {\n'
            f'    "device_name":      "{p["device_name"]}",\n'
            f'    "platform_version": "{p["platform_version"]}",\n'
            f'    "app_package":      "{p["app_package"]}",\n'
            f'    "app_activity":     "{p["app_activity"]}",\n'
            '    "no_reset":         True,\n}\nIOS = {}\n'
        )
    bl      = json.dumps(cfg.get("blacklist_ids", []))
    sec     = json.dumps(cfg.get("document_sections", []))
    od      = cfg.get("output_dir", "").replace("\\", "/")
    out_fmt = _build_output_format(cfg)
    txt = (
        f'# WHERE IS MY ID — config.py  ({datetime.now():%d.%m.%Y %H:%M})\n'
        f'PLATFORM = "{platform}"\nBLACKLIST_IDS = {bl}\n'
        f'OUTPUT_FORMAT = "{out_fmt}"\nDOCUMENT_SECTIONS = {sec}\n'
        f'OUTPUT_DIR = "{od}"\nAPPIUM_SERVER = "{cfg["appium_server"]}"\n{plat}'
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)


# ════════════════════════════════════════════════════════════════════════════
#  YARDIMCI WİDGET'LAR
# ════════════════════════════════════════════════════════════════════════════

class SecHdr(ctk.CTkFrame):
    def __init__(self, parent, title_key, color=None, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        self._title_key = title_key
        c = color or ACCENT
        ctk.CTkFrame(self, height=1, fg_color=c, corner_radius=0).pack(
            side="left", fill="x", expand=True, pady=8)
        self._lbl = ctk.CTkLabel(self, text=f"  {t(title_key)}  ", font=FB,
                                  text_color=c, fg_color="transparent")
        self._lbl.pack(side="left")
        ctk.CTkFrame(self, height=1, fg_color=c, corner_radius=0).pack(
            side="left", fill="x", expand=True, pady=8)

    def refresh(self):
        self._lbl.configure(text=f"  {t(self._title_key)}  ")


class LE(ctk.CTkFrame):
    def __init__(self, parent, label_key, var, ph_key="",
                 browse_dir=False, browse_file=False, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        self._label_key = label_key
        self._ph_key    = ph_key
        self._lbl = ctk.CTkLabel(self, text=t(label_key), font=FS,
                                  text_color=T_MUT, width=155, anchor="w")
        self._lbl.pack(side="left")
        ph = t(ph_key) if ph_key else ""
        self._entry = ctk.CTkEntry(self, textvariable=var, placeholder_text=ph,
                                    fg_color=BG_INPUT, border_color="#D8D0C0",
                                    text_color=T_PRI, font=FS, corner_radius=6)
        self._entry.pack(side="left", fill="x", expand=True, padx=(4, 0))
        if browse_dir:
            ctk.CTkButton(self, text=t("btn_browse_dir"), width=30, height=26,
                          fg_color=BG_CARD, hover_color=BG_INPUT,
                          font=FS, corner_radius=6,
                          command=lambda: self._pick(var, "dir")
                          ).pack(side="left", padx=(4, 0))
        if browse_file:
            ctk.CTkButton(self, text=t("btn_browse_file"), width=30, height=26,
                          fg_color=BG_CARD, hover_color=BG_INPUT,
                          font=FS, corner_radius=6,
                          command=lambda: self._pick(var, "file")
                          ).pack(side="left", padx=(4, 0))

    def _pick(self, var, kind):
        p = (filedialog.askdirectory() if kind == "dir"
             else filedialog.askopenfilename(
                 filetypes=[("Excel", "*.xlsx *.xls"), ("All", "*.*")]))
        if p:
            var.set(p)

    def refresh(self):
        self._lbl.configure(text=t(self._label_key))
        if self._ph_key:
            self._entry.configure(placeholder_text=t(self._ph_key))


class Badge(ctk.CTkLabel):
    _KEYS = {
        "idle":       ("badge_idle",       ACCENT_DK),
        "running":    ("badge_running",    ACCENT_DK),
        "connected":  ("badge_connected",  ACCENT_SES),
        "collecting": ("badge_collecting", C_INF),
        "finishing":  ("badge_finishing",  C_WRN),
        "ok":         ("badge_ok",         "green"),
        "error":      ("badge_error",      "red"),
    }
    def __init__(self, parent, **kw):
        super().__init__(parent, font=FB, corner_radius=8, padx=12, pady=4, **kw)
        self._current = "idle"
        self.set("idle")

    def set(self, s):
        self._current = s
        key, col = self._KEYS.get(s, self._KEYS["idle"])
        self.configure(fg_color=col, text=t(key), text_color="#FFFFFF")

    def refresh(self):
        self.set(self._current)


# ════════════════════════════════════════════════════════════════════════════
#  PROFİL PANELİ
# ════════════════════════════════════════════════════════════════════════════

class ProfilePanel(ctk.CTkFrame):
    def __init__(self, parent, platform, profiles, active, on_change=None, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        self.platform   = platform
        self._profiles  = dict(profiles)
        self._active    = (active if active in profiles
                           else (list(profiles)[0] if profiles else ""))
        self._on_change = on_change

        self.v_profile = tk.StringVar(value=self._active)
        self.v_device  = tk.StringVar()
        self.v_version = tk.StringVar()
        if platform == "ios":
            self.v_bundle = tk.StringVar()
            self.v_udid   = tk.StringVar()
        else:
            self.v_package  = tk.StringVar()
            self.v_activity = tk.StringVar()

        self._widget_refs = []   # (widget, refresh_cb) için
        self._build()
        self._load(self._active)

    def _build(self):
        col = ACCENT_IOS if self.platform == "ios" else ACCENT

        row = ctk.CTkFrame(self, fg_color="#EDE8DF", corner_radius=8)
        row.pack(fill="x", padx=14, pady=(0, 4))
        self._lbl_profile = ctk.CTkLabel(row, text=t("lbl_profile"), font=FS,
                                          text_color=T_MUT, width=50, anchor="w")
        self._lbl_profile.pack(side="left", padx=(10, 0), pady=8)
        self.dd = ctk.CTkOptionMenu(
            row, values=self._names(), variable=self.v_profile,
            fg_color=BG_INPUT, button_color=BG_CARD,
            button_hover_color=BG_PANEL, text_color=T_PRI,
            font=FS, dropdown_fg_color=BG_CARD,
            corner_radius=6, command=self._select, width=200)
        self.dd.pack(side="left", padx=(4, 8), pady=8)
        for txt_key, tc, cb in [("btn_profile_save", col,   self._save),
                                  ("btn_profile_new",  C_OK,  self._new),
                                  ("btn_profile_delete", C_ERR, self._delete)]:
            ctk.CTkButton(row, text=t(txt_key), width=40, height=26,
                          fg_color=BG_INPUT, hover_color=BG_PANEL,
                          text_color=tc, font=FS, corner_radius=6,
                          command=cb).pack(side="left", padx=(0, 4), pady=8)

        ff = ctk.CTkFrame(self, fg_color="transparent")
        ff.pack(fill="x")
        self._le_widgets = []
        if self.platform == "ios":
            fields = [
                ("Device Name",      "v_device",  ""),
                ("Platform Version", "v_version", ""),
                ("Bundle ID",        "v_bundle",  ""),
                ("UDID",             "v_udid",    ""),
            ]
        else:
            fields = [
                ("Device Name",      "v_device",   ""),
                ("Platform Version", "v_version",  ""),
                ("App Package",      "v_package",  ""),
                ("App Activity",     "v_activity", ""),
            ]
        for lbl, varname, ph in fields:
            var = getattr(self, varname)
            w = ctk.CTkFrame(ff, fg_color="transparent")
            w.pack(fill="x", padx=14, pady=2)
            lbl_w = ctk.CTkLabel(w, text=lbl, font=FS, text_color=T_MUT,
                                  width=155, anchor="w")
            lbl_w.pack(side="left")
            ctk.CTkEntry(w, textvariable=var, placeholder_text=ph,
                         fg_color=BG_INPUT, border_color="#D8D0C0",
                         text_color=T_PRI, font=FS, corner_radius=6
                         ).pack(side="left", fill="x", expand=True, padx=(4, 0))

    def _names(self):
        return list(self._profiles.keys()) or ["(empty)"]

    def _load(self, name):
        d = self._profiles.get(name, {})
        self.v_device.set(d.get("device_name", ""))
        self.v_version.set(d.get("platform_version", ""))
        if self.platform == "ios":
            self.v_bundle.set(d.get("bundle_id", ""))
            self.v_udid.set(d.get("udid", ""))
        else:
            self.v_package.set(d.get("app_package", ""))
            self.v_activity.set(d.get("app_activity", ""))

    def _to_dict(self):
        if self.platform == "ios":
            return {"device_name": self.v_device.get(),
                    "platform_version": self.v_version.get(),
                    "bundle_id":  self.v_bundle.get(),
                    "udid":       self.v_udid.get()}
        return {"device_name":  self.v_device.get(),
                "platform_version": self.v_version.get(),
                "app_package":  self.v_package.get(),
                "app_activity": self.v_activity.get()}

    def _notify(self):
        if self._on_change:
            self._on_change(self._profiles, self._active)

    def _select(self, name):
        self._active = name
        self._load(name)
        self._notify()

    def _save(self):
        name = self.v_profile.get()
        if not name or name == "(empty)":
            return
        self._profiles[name] = self._to_dict()
        self._active = name
        self.dd.configure(values=self._names())
        self._notify()
        messagebox.showinfo(t("msg_overwrite_title"),
                             t("msg_overwrite_body", name=name))

    def _new(self):
        name = simpledialog.askstring(
            t("btn_profile_new"),
            "Profile name\n(e.g. Project_1 iOS, Project_2 Android):",
            parent=self.winfo_toplevel())
        if not name or not name.strip():
            return
        name = name.strip()
        if name in self._profiles:
            messagebox.showwarning(t("msg_warn_title"),
                                    t("msg_profile_exists", name=name))
            return
        self._profiles[name] = self._to_dict()
        self._active = name
        self.v_profile.set(name)
        self.dd.configure(values=self._names())
        self._notify()

    def _delete(self):
        name = self.v_profile.get()
        if len(self._profiles) <= 1:
            messagebox.showwarning(t("msg_warn_title"), t("msg_min_profile"))
            return
        if not messagebox.askyesno(t("msg_delete_title"),
                                    t("msg_delete_confirm", name=name)):
            return
        del self._profiles[name]
        first = list(self._profiles)[0]
        self._active = first
        self.v_profile.set(first)
        self.dd.configure(values=self._names())
        self._load(first)
        self._notify()

    def refresh(self):
        self._lbl_profile.configure(text=t("lbl_profile"))

    def get_active(self): return self._active
    def get_data(self):   return self._profiles.get(self._active, {})
    def get_all(self):    return self._profiles


# ════════════════════════════════════════════════════════════════════════════
#  ANA UYGULAMA
# ════════════════════════════════════════════════════════════════════════════

class App(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self._proc   = None
        self._pn_ev  = threading.Event()
        self._pn_ans = ""
        self._ow_ev  = threading.Event()
        self._ow_ans = True

        self._active_tab = "tam"

        # Dil başlangıcı — config'den
        set_lang(self.cfg.get("language", "TR"))
        on_lang_change(self._on_lang_changed)

        self.title(t("app_title"))
        self.geometry("1160x840")
        self.minsize(980, 680)
        self.configure(fg_color="#F5F0E8")

        self._mk_vars()
        self._mk_ui()
        self._apply_cfg()

    # ── Dil değişimi ──────────────────────────────────────────────────────────
    def _on_lang_changed(self, lang: str):
        """i18n listener — dil değişince tüm UI'ı yenile."""
        self.cfg["language"] = lang
        self._refresh_all_ui()

    def _refresh_all_ui(self):
        """Tüm widget text'lerini aktif dile göre günceller."""
        # Header
        self._lbl_subtitle.configure(text=t("app_subtitle"))
        self._lbl_version.configure(text=t("app_version"))
        self.badge.refresh()
        self._lbl_lang.configure(text=t("lang_label"))

        # Footer butonlar
        self.btn_run.configure(text=t("btn_run"))
        self.btn_smart_connect.configure(text=t("btn_connect"))
        self.btn_session_start.configure(text=t("btn_session_start"))
        self.btn_session_collect.configure(text=t("btn_session_collect"))
        self.btn_session_finish.configure(text=t("btn_session_finish"))
        self.btn_stop.configure(text=t("btn_stop"))
        self.btn_summary.configure(text=t("btn_merge_sheets"))
        self._lbl_excel_footer.configure(text=t("lbl_excel"))
        self.xl_entry.configure(placeholder_text=t("ph_excel"))

        # Tab butonlar
        self.btn_tab_tam.configure(text=t("tab_full_scan"))
        self.btn_tab_smart.configure(text=t("tab_smart_scan"))
        self.btn_tab_session.configure(text=t("tab_session_scan"))

        # Config paneli
        self._refresh_config_panel()

        # Log başlıkları
        self._lbl_console_full.configure(text=t("console_title_full"))
        self._btn_clear_full.configure(text=t("btn_clear"))
        self._lbl_console_smart.configure(text=t("console_title_smart"))
        self._btn_clear_smart.configure(text=t("btn_clear"))
        self._lbl_console_session.configure(text=t("console_title_session"))
        self._lbl_session_hint.configure(text=t("session_hint"))
        self._btn_clear_session.configure(text=t("btn_clear"))

        # Session table header
        for lbl, key in zip(self._tbl_hdr_labels,
                             ["tbl_col_scan", "tbl_col_unique", "tbl_col_undef",
                              "tbl_col_dup", "tbl_col_miss", "tbl_col_total"]):
            lbl.configure(text=t(key))

        # Flow input
        self._lbl_flow.configure(text=t("lbl_flow_name"))
        self._flow_entry.configure(placeholder_text=t("ph_flow_name"))

        # Page input (tam tarama)
        self._lbl_page_full.configure(text=t("lbl_page_name"))
        self._page_entry_full.configure(placeholder_text=t("ph_page_name"))
        self._btn_submit_page.configure(text=t("btn_send"))

        # Page input (smart)
        self._lbl_page_smart.configure(text=t("lbl_page_name"))
        self._page_entry_smart.configure(placeholder_text=t("ph_smart_page"))
        self._btn_submit_smart.configure(text=t("btn_send_report"))

        # Overwrite frame
        self._btn_ow_yes.configure(text=t("btn_yes_overwrite"))
        self._btn_ow_no.configure(text=t("btn_no_cancel"))

        # Platform label
        self._upd_label()

        # Session table yenile
        if hasattr(self, '_session_ref'):
            self.after(0, self._update_session_table)

    def _refresh_config_panel(self):
        self._btn_plat_ios.configure(text=t("btn_ios"))
        self._btn_plat_and.configure(text=t("btn_android"))

        for hdr in self._sec_hdrs:
            hdr.refresh()

        self._le_appium.refresh()
        self._le_outdir.refresh()

        self._lbl_fmt.configure(text=t("lbl_output_format"))
        self._cb_word.configure(text=t("fmt_word"))
        self._cb_excel.configure(text=t("fmt_excel"))
        self._cb_json.configure(text=t("fmt_json"))

        self._cb_unique.configure(text=t("sec_unique"))
        self._cb_undefined.configure(text=t("sec_undefined"))
        self._cb_duplicate.configure(text=t("sec_duplicate"))
        self._cb_missing.configure(text=t("sec_missing"))

        self.ios_panel.refresh()
        self.and_panel.refresh()

        self._lbl_blacklist.configure(text=t("lbl_comma_sep"))

    def _mk_vars(self):
        self.v_platform      = tk.StringVar(value="ios")
        self.v_out_word      = tk.BooleanVar(value=True)
        self.v_out_excel     = tk.BooleanVar(value=True)
        self.v_out_json      = tk.BooleanVar(value=False)
        self.v_out_dir       = tk.StringVar()
        self.v_appium        = tk.StringVar()
        self.v_blacklist     = tk.StringVar()
        self.v_summary_xl    = tk.StringVar()
        self.v_sec_unique    = tk.BooleanVar(value=True)
        self.v_sec_undefined = tk.BooleanVar(value=True)
        self.v_sec_duplicate = tk.BooleanVar(value=True)
        self.v_sec_missing   = tk.BooleanVar(value=True)
        self.v_lang          = tk.StringVar(value=get_lang())

    def _apply_cfg(self):
        c = self.cfg
        self.v_platform.set(c["platform"])
        self.v_out_word.set(c.get("output_word", True))
        self.v_out_excel.set(c.get("output_excel", True))
        self.v_out_json.set(c.get("output_json", False))
        self.v_out_dir.set(c["output_dir"])
        self.v_appium.set(c["appium_server"])
        self.v_blacklist.set(", ".join(c.get("blacklist_ids", [])))
        secs = c.get("document_sections", [])
        self.v_sec_unique.set("unique" in secs)
        self.v_sec_undefined.set("undefined" in secs)
        self.v_sec_duplicate.set("duplicate" in secs)
        self.v_sec_missing.set("missing" in secs)
        self._toggle_platform(c["platform"], init=True)

    # ── UI inşa ──────────────────────────────────────────────────────────────
    def _mk_ui(self):
        self._mk_header()
        self._mk_footer()
        self._mk_body()

    def _mk_header(self):
        hdr = ctk.CTkFrame(self, fg_color="white", corner_radius=0, height=54)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text=t("app_title"),
                     font=FT, text_color="black").pack(side="left", padx=20)
        self._lbl_subtitle = ctk.CTkLabel(hdr, text=t("app_subtitle"),
                                           font=FS, text_color="black")
        self._lbl_subtitle.pack(side="left", padx=4)

        # ── Dil seçici (sağ üst köşe) ────────────────────────────────────────
        lang_frame = ctk.CTkFrame(hdr, fg_color="#EDE8DF", corner_radius=8)
        lang_frame.pack(side="right", padx=(0, 12), pady=8)

        self._lbl_lang = ctk.CTkLabel(lang_frame, text=t("lang_label"),
                                       font=FS, text_color=T_MUT)
        self._lbl_lang.pack(side="left", padx=(10, 4))

        self._lang_menu = ctk.CTkOptionMenu(
            lang_frame,
            values=available_langs(),
            variable=self.v_lang,
            fg_color=BG_INPUT,
            button_color=ACCENT_IOS,
            button_hover_color=ACCENT_IOS_DK,
            text_color=T_PRI,
            font=FB,
            dropdown_fg_color=BG_PANEL,
            corner_radius=6,
            width=70,
            command=self._change_lang,
        )
        self._lang_menu.pack(side="left", padx=(0, 8), pady=6)
        # ─────────────────────────────────────────────────────────────────────

        self.badge = Badge(hdr)
        self.badge.pack(side="right", padx=4)
        self._lbl_version = ctk.CTkLabel(hdr, text=t("app_version"),
                                          font=FB, text_color="black")
        self._lbl_version.pack(side="right", padx=4)

    def _change_lang(self, lang: str):
        set_lang(lang)   # i18n listener _on_lang_changed'i tetikler

    def _mk_footer(self):
        foot = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0, height=66)
        foot.pack(fill="x", side="bottom")
        foot.pack_propagate(False)

        lf = ctk.CTkFrame(foot, fg_color="transparent")
        lf.pack(side="left", padx=(12, 0), pady=10)

        self.lbl_prof = ctk.CTkLabel(lf, text="", font=FS, text_color=T_MUT)
        self.lbl_prof.pack(side="left", padx=(4, 12))

        self.btn_run = ctk.CTkButton(
            lf, text=t("btn_run"), font=FL, height=44, width=150,
            fg_color="#1a8242", hover_color="#145c30",
            text_color="#FFFFFF", corner_radius=8,
            command=self._run_checker)

        self.btn_smart_connect = ctk.CTkButton(
            lf, text=t("btn_connect"), font=FL, height=44, width=220,
            fg_color=ACCENT_IOS, hover_color=ACCENT_IOS_DK,
            text_color="#FFFFFF", corner_radius=8,
            command=self._smart_connect)

        self.btn_session_start = ctk.CTkButton(
            lf, text=t("btn_session_start"), font=FL, height=44, width=200,
            fg_color=ACCENT_SES, hover_color=ACCENT_SES_DK,
            text_color="#FFFFFF", corner_radius=8,
            command=self._session_start)

        self.btn_session_collect = ctk.CTkButton(
            lf, text=t("btn_session_collect"), font=FL, height=44, width=180,
            fg_color=ACCENT_IOS, hover_color=ACCENT_IOS_DK,
            text_color="#FFFFFF", corner_radius=8,
            command=self._session_collect)

        self.btn_session_finish = ctk.CTkButton(
            lf, text=t("btn_session_finish"), font=FL, height=44, width=230,
            fg_color="#8C6A10", hover_color="#6a4e0c",
            text_color="#FFFFFF", corner_radius=8,
            command=self._session_finish)

        self.btn_stop = ctk.CTkButton(
            lf, text=t("btn_stop"), font=FL, height=44, width=120,
            fg_color="#7B1515", hover_color="#5a0f0f",
            text_color="#FFFFFF", corner_radius=8,
            command=self._stop_proc)

        # Sağ: Excel seç + Build Summary
        rf = ctk.CTkFrame(foot, fg_color="transparent")
        rf.pack(side="right", padx=12, pady=10)

        sb = ctk.CTkFrame(rf, fg_color="#F5F0E8", corner_radius=8,
                          border_width=1, border_color="#D8D0C0")
        sb.pack(side="right")
        self._lbl_excel_footer = ctk.CTkLabel(sb, text=t("lbl_excel"), font=FS,
                                               text_color="#8C7D6A")
        self._lbl_excel_footer.pack(side="left", padx=(10, 4), pady=8)
        self.xl_entry = ctk.CTkEntry(
            sb, textvariable=self.v_summary_xl,
            placeholder_text=t("ph_excel"),
            fg_color="#EDE8DF", border_color="#D8D0C0",
            text_color="#1a8242", font=FS, width=220, corner_radius=6)
        self.xl_entry.pack(side="left", pady=8)
        ctk.CTkButton(sb, text=t("btn_browse_file"), width=30, height=28,
                      fg_color="#EDE8DF", hover_color="#D8D0C0",
                      font=FS, corner_radius=6,
                      command=self._pick_excel).pack(side="left", padx=(4, 4), pady=8)
        self.btn_summary = ctk.CTkButton(
            sb, text=t("btn_merge_sheets"), font=FL, height=36, width=155,
            fg_color="#1a8242", hover_color="#145c30",
            text_color="#FFFFFF", corner_radius=6,
            command=self._run_summary)
        self.btn_summary.pack(side="left", padx=(0, 8), pady=8)

    def _mk_body(self):
        self._body_frame = ctk.CTkFrame(self, fg_color="#F5F0E8", corner_radius=0)
        self._body_frame.pack(fill="both", expand=True, padx=12, pady=(8, 4))
        self._body_frame.columnconfigure(0, weight=0)
        self._body_frame.columnconfigure(1, weight=1)
        self._body_frame.rowconfigure(0, weight=0)
        self._body_frame.rowconfigure(1, weight=1)

        tab_bar = ctk.CTkFrame(self._body_frame, fg_color="#FFFFFF",
                               corner_radius=8, height=42)
        tab_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        tab_bar.grid_propagate(False)

        self.btn_tab_tam = ctk.CTkButton(
            tab_bar, text=t("tab_full_scan"), font=FL, height=34,
            fg_color=ACCENT_IOS, hover_color=ACCENT_IOS_DK,
            text_color="#FFFFFF", corner_radius=7, width=160,
            command=lambda: self._switch_tab("tam"))
        self.btn_tab_tam.pack(side="left", padx=(8, 4), pady=4)

        self.btn_tab_smart = ctk.CTkButton(
            tab_bar, text=t("tab_smart_scan"), font=FL, height=34,
            fg_color=BG_INPUT, hover_color="#E8E0D0",
            text_color=T_MUT, corner_radius=7, width=160,
            command=lambda: self._switch_tab("smart"))
        self.btn_tab_smart.pack(side="left", padx=(0, 4), pady=4)

        self.btn_tab_session = ctk.CTkButton(
            tab_bar, text=t("tab_session_scan"), font=FL, height=34,
            fg_color=BG_INPUT, hover_color="#E8E0D0",
            text_color=T_MUT, corner_radius=7, width=170,
            command=lambda: self._switch_tab("session"))
        self.btn_tab_session.pack(side="left", padx=(0, 4), pady=4)

        self.left_panel = ctk.CTkScrollableFrame(
            self._body_frame, width=430, fg_color="#FFFFFF",
            corner_radius=10, scrollbar_button_color="#D8D0C0")
        self.left_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        self._mk_config(self.left_panel)

        self.right_tam = ctk.CTkFrame(self._body_frame, fg_color="#F5F0E8",
                                       corner_radius=10)
        self.right_tam.grid(row=1, column=1, sticky="nsew")
        self._mk_log(self.right_tam)

        self.right_smart = ctk.CTkFrame(self._body_frame, fg_color="#F5F0E8",
                                         corner_radius=10)
        self._mk_smart_log(self.right_smart)

        self.right_session = ctk.CTkFrame(self._body_frame, fg_color="#F5F0E8",
                                           corner_radius=10)
        self._mk_session_panel(self.right_session)

        self._switch_tab("tam", init=True)

    # ── Tab değiştirme ────────────────────────────────────────────────────────
    def _switch_tab(self, tab: str, init: bool = False):
        self._active_tab = tab

        self.btn_run.pack_forget()
        self.btn_smart_connect.pack_forget()
        self.btn_session_start.pack_forget()
        self.btn_session_collect.pack_forget()
        self.btn_session_finish.pack_forget()
        self.btn_stop.pack_forget()

        for btn, tab_id in [(self.btn_tab_tam,     "tam"),
                            (self.btn_tab_smart,   "smart"),
                            (self.btn_tab_session, "session")]:
            if tab_id == tab:
                col = ACCENT_SES if tab_id == "session" else ACCENT_IOS
                dk  = ACCENT_SES_DK if tab_id == "session" else ACCENT_IOS_DK
                btn.configure(fg_color=col, hover_color=dk, text_color="#FFFFFF")
            else:
                btn.configure(fg_color=BG_INPUT, hover_color="#E8E0D0", text_color=T_MUT)

        for panel in [self.right_tam, self.right_smart, self.right_session]:
            panel.grid_remove()

        if tab == "tam":
            self.right_tam.grid(row=1, column=1, sticky="nsew")
            self.btn_run.pack(side="left", padx=(0, 6))
            self.btn_stop.pack(side="left")

        elif tab == "smart":
            self.right_smart.grid(row=1, column=1, sticky="nsew")
            self.btn_smart_connect.pack(side="left", padx=(0, 6))
            self.btn_stop.pack(side="left")

        else:
            self.right_session.grid(row=1, column=1, sticky="nsew")
            self._refresh_session_footer()
            self.btn_stop.pack(side="left")

    def _refresh_session_footer(self):
        self.btn_session_start.pack_forget()
        self.btn_session_collect.pack_forget()
        self.btn_session_finish.pack_forget()

        if not hasattr(self, '_session_ref'):
            self.btn_session_start.pack(side="left", padx=(0, 6))
            return

        st = getattr(self, '_session_state', 'idle')
        if st == "idle":
            self.btn_session_start.pack(side="left", padx=(0, 6))
        elif st in ("connected", "collecting"):
            self.btn_session_collect.pack(side="left", padx=(0, 6))
            self.btn_session_finish.pack(side="left", padx=(0, 6))

    def _set_session_state(self, state: str):
        self._session_state = state

        if state == "idle":
            self.badge.set("idle")
            self.btn_stop.configure(state="disabled")
            self.btn_summary.configure(state="normal")
            if hasattr(self, '_flow_entry'):
                self._flow_entry.configure(state="normal", fg_color=BG_INPUT)
                self._flow_active_label.configure(text="")
        elif state == "connected":
            self.badge.set("connected")
            self.btn_stop.configure(state="normal")
            self.btn_summary.configure(state="disabled")
            self.btn_session_collect.configure(state="normal",
                fg_color=ACCENT_IOS, hover_color=ACCENT_IOS_DK)
            self.btn_session_finish.configure(state="normal",
                fg_color="#8C6A10", hover_color="#6a4e0c")
        elif state == "collecting":
            self.badge.set("collecting")
            self.btn_session_collect.configure(state="disabled", fg_color="#9E9E9E")
            self.btn_session_finish.configure(state="disabled", fg_color="#9E9E9E")
        elif state == "finishing":
            self.badge.set("finishing")
            self.btn_session_collect.configure(state="disabled", fg_color="#9E9E9E")
            self.btn_session_finish.configure(state="disabled", fg_color="#9E9E9E")
            self.btn_stop.configure(state="disabled")

        if self._active_tab == "session":
            self._refresh_session_footer()

    # ── Session panel ─────────────────────────────────────────────────────────
    def _mk_session_panel(self, p):
        p.rowconfigure(0, weight=0)
        p.rowconfigure(1, weight=0)
        p.rowconfigure(2, weight=1)
        p.rowconfigure(3, weight=0)
        p.columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(p, fg_color="white", corner_radius=0, height=36)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        self._lbl_console_session = ctk.CTkLabel(hdr, text=t("console_title_session"),
                                                   font=FB, text_color=ACCENT_SES)
        self._lbl_console_session.pack(side="left", padx=14)
        self._lbl_session_hint = ctk.CTkLabel(hdr, text=t("session_hint"),
                                               font=FS, text_color=T_MUT)
        self._lbl_session_hint.pack(side="left", padx=8)
        self._btn_clear_session = ctk.CTkButton(
            hdr, text=t("btn_clear"), font=FS, width=70, height=24,
            fg_color="#7B1515", hover_color="#5a0f0f",
            text_color="white", corner_radius=6,
            command=self._clear_session_log)
        self._btn_clear_session.pack(side="right", padx=10, pady=5)

        inp = ctk.CTkFrame(p, fg_color=BG_CARD, corner_radius=0, height=46)
        inp.grid(row=1, column=0, sticky="ew")
        inp.grid_propagate(False)

        self._lbl_flow = ctk.CTkLabel(inp, text=t("lbl_flow_name"),
                                       font=FL, text_color="black")
        self._lbl_flow.pack(side="left", padx=(14, 6), pady=8)
        self.v_session_flow = tk.StringVar()
        self._flow_entry = ctk.CTkEntry(
            inp, textvariable=self.v_session_flow,
            placeholder_text=t("ph_flow_name"),
            fg_color=BG_INPUT, border_color=ACCENT_SES,
            text_color=T_PRI, font=FL, width=220, corner_radius=6)
        self._flow_entry.pack(side="left", pady=8)
        self._flow_entry.bind("<Return>", lambda e: self._session_start())

        self._flow_active_label = ctk.CTkLabel(inp, text="", font=FB,
                                                text_color=ACCENT_SES)
        self._flow_active_label.pack(side="left", padx=(16, 0), pady=8)

        tbl_outer = ctk.CTkFrame(p, fg_color=BG_MAIN, corner_radius=0)
        tbl_outer.grid(row=2, column=0, sticky="nsew")
        tbl_outer.rowconfigure(1, weight=1)
        tbl_outer.columnconfigure(0, weight=1)

        tbl_hdr = ctk.CTkFrame(tbl_outer, fg_color=ACCENT_SES,
                                corner_radius=0, height=28)
        tbl_hdr.grid(row=0, column=0, sticky="ew")
        tbl_hdr.grid_propagate(False)
        self._tbl_hdr_labels = []
        for col_key, w in [("tbl_col_scan", 200), ("tbl_col_unique", 70),
                            ("tbl_col_undef", 70), ("tbl_col_dup", 70),
                            ("tbl_col_miss", 70), ("tbl_col_total", 70)]:
            lbl = ctk.CTkLabel(tbl_hdr, text=t(col_key), font=FB,
                               text_color="white", width=w, anchor="center")
            lbl.pack(side="left", padx=2)
            self._tbl_hdr_labels.append(lbl)

        self._session_table_frame = ctk.CTkScrollableFrame(
            tbl_outer, fg_color=BG_PANEL, corner_radius=0,
            scrollbar_button_color="#D8D0C0")
        self._session_table_frame.grid(row=1, column=0, sticky="nsew")

        self.session_log_box = ctk.CTkTextbox(
            p, fg_color="#FAFAF7", text_color=T_PRI,
            font=FLG, corner_radius=0, wrap="word",
            scrollbar_button_color="#D8D0C0", height=160)
        self.session_log_box.grid(row=3, column=0, sticky="ew")
        for tag, col in [("ok", C_OK), ("err", C_ERR),
                          ("warn", C_WRN), ("info", C_INF), ("dim", T_MUT)]:
            self.session_log_box._textbox.tag_config(tag, foreground=col)

        self._session_ref = SessionTab(self)
        self._session_ref.bind_log(self.session_log_box)
        self._session_ref.bind_table_callback(self._update_session_table)
        self._session_state = "idle"

    def _update_session_table(self):
        for w in self._session_table_frame.winfo_children():
            w.destroy()

        summary = self._session_ref.summary
        if not summary:
            ctk.CTkLabel(self._session_table_frame,
                         text=t("tbl_no_scan"),
                         font=FS, text_color=T_MUT).pack(pady=20)
            return

        totals = {"unique": 0, "undefined": 0, "duplicate": 0, "missing": 0, "total": 0}

        for i, s in enumerate(summary):
            bg = BG_PANEL if i % 2 == 0 else BG_CARD
            row = ctk.CTkFrame(self._session_table_frame,
                               fg_color=bg, corner_radius=0, height=28)
            row.pack(fill="x")
            row.pack_propagate(False)
            vals = [
                (s["label"],    200, T_PRI,     True),
                (s["unique"],    70, C_OK,      False),
                (s["undefined"], 70, C_WRN,     False),
                (s["duplicate"], 70, "#7B3F00", False),
                (s["missing"],   70, C_ERR,     False),
                (s["total"],     70, T_PRI,     True),
            ]
            for val, w, col, bold in vals:
                ctk.CTkLabel(row, text=str(val), font=FB if bold else FS,
                             text_color=col, width=w,
                             anchor="center").pack(side="left", padx=2)
            for k in totals:
                totals[k] += s.get(k, 0)

        flow = self._session_ref.flow_name if hasattr(self, '_session_ref') else ""
        tot_row = ctk.CTkFrame(self._session_table_frame,
                               fg_color=ACCENT_SES, corner_radius=0, height=28)
        tot_row.pack(fill="x", pady=(2, 0))
        tot_row.pack_propagate(False)
        tot_vals = [
            (f"{flow}  ({len(summary)} {t('tbl_col_scan').lower()})", 200, "white", True),
            (totals["unique"],    70, "white", True),
            (totals["undefined"], 70, "white", True),
            (totals["duplicate"], 70, "white", True),
            (totals["missing"],   70, "white", True),
            (totals["total"],     70, "white", True),
        ]
        for val, w, col, bold in tot_vals:
            ctk.CTkLabel(tot_row, text=str(val), font=FB if bold else FS,
                         text_color=col, width=w,
                         anchor="center").pack(side="left", padx=2)

    def _clear_session_log(self):
        self.session_log_box.configure(state="normal")
        self.session_log_box.delete("1.0", "end")
        self.session_log_box.configure(state="disabled")

    def _session_start(self):
        if hasattr(self, '_session_ref'):
            flow = self.v_session_flow.get().strip()
            if not flow:
                messagebox.showwarning(t("msg_flow_title"), t("msg_flow_empty"))
                return
            self._flow_entry.configure(state="disabled", fg_color="#D8D0C0")
            self._flow_active_label.configure(
                text=t("flow_active_label", flow=flow))
            self._session_ref.start_session(flow)

    def _session_collect(self):
        if hasattr(self, '_session_ref'):
            self._session_ref.collect_page()

    def _session_finish(self):
        if hasattr(self, '_session_ref'):
            self._session_ref.finish_session()

    def _smart_connect(self):
        if hasattr(self, '_smart_tab_ref') and self._smart_tab_ref:
            self._smart_tab_ref.run_connect_from_footer()

    # ── Smart log paneli ──────────────────────────────────────────────────────
    def _mk_smart_log(self, p):
        p.rowconfigure(1, weight=1)
        p.rowconfigure(2, weight=0)
        p.rowconfigure(3, weight=0)
        p.columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(p, fg_color="white", corner_radius=0, height=36)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        self._lbl_console_smart = ctk.CTkLabel(hdr, text=t("console_title_smart"),
                                                font=FB, text_color="green")
        self._lbl_console_smart.pack(side="left", padx=14)
        self._btn_clear_smart = ctk.CTkButton(
            hdr, text=t("btn_clear"), font=FS, width=70, height=24,
            fg_color="#7B1515", hover_color="#5a0f0f",
            text_color="white", corner_radius=6,
            command=self._clear_smart_log)
        self._btn_clear_smart.pack(side="right", padx=10, pady=5)

        self.smart_log_box = ctk.CTkTextbox(
            p, fg_color="#FAFAF7", text_color=T_PRI,
            font=FLG, corner_radius=0, wrap="word",
            scrollbar_button_color="#D8D0C0")
        self.smart_log_box.grid(row=1, column=0, sticky="nsew")
        for tag, col in [("ok", C_OK), ("err", C_ERR),
                          ("warn", C_WRN), ("info", C_INF), ("dim", T_MUT)]:
            self.smart_log_box._textbox.tag_config(tag, foreground=col)

        self.smart_page_frame = ctk.CTkFrame(p, fg_color=BG_CARD,
                                              corner_radius=0, height=50)
        self.smart_page_frame.grid(row=2, column=0, sticky="ew")
        self.smart_page_frame.grid_propagate(False)
        self.smart_page_frame.grid_remove()

        self._lbl_page_smart = ctk.CTkLabel(self.smart_page_frame,
                                             text=t("lbl_page_name"),
                                             font=FL, text_color="black")
        self._lbl_page_smart.pack(side="left", padx=(14, 6), pady=10)
        self.v_smart_page = tk.StringVar()
        self._page_entry_smart = ctk.CTkEntry(
            self.smart_page_frame, textvariable=self.v_smart_page,
            placeholder_text=t("ph_smart_page"),
            fg_color=BG_INPUT, border_color="green",
            text_color=T_PRI, font=FL, width=200, corner_radius=6)
        self._page_entry_smart.pack(side="left", pady=10)
        self._page_entry_smart.bind("<Return>", lambda e: self._smart_submit_page())
        self._btn_submit_smart = ctk.CTkButton(
            self.smart_page_frame, text=t("btn_send_report"),
            font=FL, height=32, width=160,
            fg_color="green", hover_color="#145c30",
            text_color=BG_MAIN, corner_radius=6,
            command=self._smart_submit_page)
        self._btn_submit_smart.pack(side="left", padx=10, pady=10)

        self._smart_tab_ref = SmartTab(self)
        self._smart_tab_ref.bind_to_log(self.smart_log_box)
        self._smart_tab_ref.bind_page_frame(
            self.smart_page_frame, self.v_smart_page, self._smart_submit_page)

    def _clear_smart_log(self):
        self.smart_log_box.configure(state="normal")
        self.smart_log_box.delete("1.0", "end")
        self.smart_log_box.configure(state="disabled")

    def _smart_submit_page(self):
        if hasattr(self, '_smart_tab_ref') and self._smart_tab_ref:
            self._smart_tab_ref.submit_page(self.v_smart_page.get().strip())

    # ── Config paneli ─────────────────────────────────────────────────────────
    def _mk_config(self, p):
        pad = dict(padx=14, pady=3)
        self._sec_hdrs = []

        hdr_platform = SecHdr(p, "sec_platform")
        hdr_platform.pack(fill="x", **pad)
        self._sec_hdrs.append(hdr_platform)

        pf = ctk.CTkFrame(p, fg_color="#EDE8DF", corner_radius=8)
        pf.pack(fill="x", padx=14, pady=(0, 8))
        self._btn_plat_ios = ctk.CTkButton(
            pf, text=t("btn_ios"), font=FL, height=38, corner_radius=7,
            fg_color=ACCENT_IOS, hover_color=ACCENT_IOS_DK, text_color=BG_MAIN,
            command=lambda: self._toggle_platform("ios"))
        self._btn_plat_ios.pack(side="left", expand=True, fill="x", padx=(6, 3), pady=6)
        self._btn_plat_and = ctk.CTkButton(
            pf, text=t("btn_android"), font=FL, height=38, corner_radius=7,
            fg_color=BG_INPUT, hover_color="#E8E0D0", text_color=T_MUT,
            command=lambda: self._toggle_platform("android"))
        self._btn_plat_and.pack(side="left", expand=True, fill="x", padx=(3, 6), pady=6)

        hdr_general = SecHdr(p, "sec_general")
        hdr_general.pack(fill="x", **pad)
        self._sec_hdrs.append(hdr_general)

        self._le_appium = LE(p, "lbl_appium_server", self.v_appium, "ph_appium")
        self._le_appium.pack(fill="x", padx=14, pady=3)
        self._le_outdir = LE(p, "lbl_output_dir", self.v_out_dir,
                              "ph_output_dir", browse_dir=True)
        self._le_outdir.pack(fill="x", padx=14, pady=3)

        fmt_row = ctk.CTkFrame(p, fg_color="transparent")
        fmt_row.pack(fill="x", padx=14, pady=3)
        self._lbl_fmt = ctk.CTkLabel(fmt_row, text=t("lbl_output_format"), font=FS,
                                      text_color=T_MUT, width=155, anchor="w")
        self._lbl_fmt.pack(side="left")
        fmt_box = ctk.CTkFrame(fmt_row, fg_color="#EDE8DF", corner_radius=6)
        fmt_box.pack(side="left", fill="x", expand=True, padx=(4, 0))
        self._cb_word = ctk.CTkCheckBox(
            fmt_box, text=t("fmt_word"), variable=self.v_out_word, font=FS,
            text_color=T_PRI, fg_color="#185FA5", hover_color="#185FA5",
            checkmark_color="#FFFFFF", border_color="#B0A898",
            command=self._validate_output_format)
        self._cb_word.pack(anchor="w", padx=(10, 6), pady=6)
        self._cb_excel = ctk.CTkCheckBox(
            fmt_box, text=t("fmt_excel"), variable=self.v_out_excel, font=FS,
            text_color=T_PRI, fg_color="#2D6A2D", hover_color="#2D6A2D",
            checkmark_color="#FFFFFF", border_color="#B0A898",
            command=self._validate_output_format)
        self._cb_excel.pack(anchor="w", padx=(10, 6), pady=6)
        self._cb_json = ctk.CTkCheckBox(
            fmt_box, text=t("fmt_json"), variable=self.v_out_json, font=FS,
            text_color=T_PRI, fg_color="#8C6A10", hover_color="#8C6A10",
            checkmark_color="#FFFFFF", border_color="#B0A898",
            command=self._validate_output_format)
        self._cb_json.pack(anchor="w", padx=(10, 6), pady=6)

        hdr_sections = SecHdr(p, "sec_report_sections")
        hdr_sections.pack(fill="x", **pad)
        self._sec_hdrs.append(hdr_sections)

        sf = ctk.CTkFrame(p, fg_color="#EDE8DF", corner_radius=8)
        sf.pack(fill="x", padx=14, pady=(0, 8))
        self._cb_unique = ctk.CTkCheckBox(sf, text=t("sec_unique"),
            variable=self.v_sec_unique, font=FS, text_color=T_PRI,
            fg_color="white", hover_color="white",
            checkmark_color="#1a8242", border_color="#B0A898")
        self._cb_unique.pack(anchor="w", padx=12, pady=4)
        self._cb_undefined = ctk.CTkCheckBox(sf, text=t("sec_undefined"),
            variable=self.v_sec_undefined, font=FS, text_color=T_PRI,
            fg_color="white", hover_color="white",
            checkmark_color="#1a8242", border_color="#B0A898")
        self._cb_undefined.pack(anchor="w", padx=12, pady=4)
        self._cb_duplicate = ctk.CTkCheckBox(sf, text=t("sec_duplicate"),
            variable=self.v_sec_duplicate, font=FS, text_color=T_PRI,
            fg_color="white", hover_color="white",
            checkmark_color="#1a8242", border_color="#B0A898")
        self._cb_duplicate.pack(anchor="w", padx=12, pady=4)
        self._cb_missing = ctk.CTkCheckBox(sf, text=t("sec_missing"),
            variable=self.v_sec_missing, font=FS, text_color=T_PRI,
            fg_color="white", hover_color="white",
            checkmark_color="#1a8242", border_color="#B0A898")
        self._cb_missing.pack(anchor="w", padx=12, pady=4)

        self.ios_hdr = SecHdr(p, "sec_ios", color=ACCENT)
        self.ios_hdr.pack(fill="x", **pad)
        self._sec_hdrs.append(self.ios_hdr)
        self.ios_panel = ProfilePanel(
            p, "ios",
            profiles=self.cfg.get("ios_profiles", {"PIA iOS": _D_IOS.copy()}),
            active=self.cfg.get("active_ios_profile", "PIA iOS"),
            on_change=self._ios_changed)
        self.ios_panel.pack(fill="x", pady=(0, 6))

        self.and_hdr = SecHdr(p, "sec_android", color=ACCENT)
        self.and_hdr.pack(fill="x", **pad)
        self._sec_hdrs.append(self.and_hdr)
        self.and_panel = ProfilePanel(
            p, "android",
            profiles=self.cfg.get("android_profiles", {"PIA Android": _D_AND.copy()}),
            active=self.cfg.get("active_android_profile", "PIA Android"),
            on_change=self._and_changed)
        self.and_panel.pack(fill="x", pady=(0, 6))

        self.bl_hdr = SecHdr(p, "sec_blacklist")
        self.bl_hdr.pack(fill="x", **pad)
        self._sec_hdrs.append(self.bl_hdr)
        self.bl_frame = ctk.CTkFrame(p, fg_color="transparent")
        self.bl_frame.pack(fill="x", padx=14, pady=(0, 10))
        self._lbl_blacklist = ctk.CTkLabel(self.bl_frame, text=t("lbl_comma_sep"),
                                            font=FS, text_color=T_MUT)
        self._lbl_blacklist.pack(anchor="w")
        ctk.CTkEntry(self.bl_frame, textvariable=self.v_blacklist,
                     fg_color=BG_INPUT, border_color="#D8D0C0",
                     text_color=T_PRI, font=FS, corner_radius=6
                     ).pack(fill="x", pady=(2, 0))

    def _validate_output_format(self):
        if not any([self.v_out_word.get(), self.v_out_excel.get(), self.v_out_json.get()]):
            self.v_out_word.set(True)
            messagebox.showwarning(t("msg_output_fmt_warn"), t("msg_min_output_fmt"))

    # ── Log paneli (Tam Tarama) ───────────────────────────────────────────────
    def _mk_log(self, p):
        p.rowconfigure(1, weight=1)
        p.rowconfigure(2, weight=0)
        p.columnconfigure(0, weight=1)
        hdr = ctk.CTkFrame(p, fg_color="white", corner_radius=0, height=36)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        self._lbl_console_full = ctk.CTkLabel(hdr, text=t("console_title_full"),
                                               font=FB, text_color="green")
        self._lbl_console_full.pack(side="left", padx=14)
        self._btn_clear_full = ctk.CTkButton(
            hdr, text=t("btn_clear"), font=FS, width=70, height=24,
            fg_color="#7B1515", hover_color="#5a0f0f",
            text_color="white", corner_radius=6,
            command=self._clear_log)
        self._btn_clear_full.pack(side="right", padx=10, pady=5)

        self.log_box = ctk.CTkTextbox(
            p, fg_color="#FAFAF7", text_color=T_PRI,
            font=FLG, corner_radius=0, wrap="word",
            scrollbar_button_color="#D8D0C0")
        self.log_box.grid(row=1, column=0, sticky="nsew")
        for tag, col in [("ok", C_OK), ("err", C_ERR),
                          ("warn", C_WRN), ("info", C_INF), ("dim", T_MUT)]:
            self.log_box._textbox.tag_config(tag, foreground=col)

        self.page_input_frame = ctk.CTkFrame(p, fg_color=BG_CARD,
                                              corner_radius=0, height=50)
        self.page_input_frame.grid(row=2, column=0, sticky="ew")
        self.page_input_frame.grid_propagate(False)
        self.page_input_frame.grid_remove()
        p.rowconfigure(2, weight=0)

        self._lbl_page_full = ctk.CTkLabel(self.page_input_frame,
                                            text=t("lbl_page_name"),
                                            font=FL, text_color="black")
        self._lbl_page_full.pack(side="left", padx=(14, 6), pady=10)
        self.v_page = tk.StringVar()
        self._page_entry_full = ctk.CTkEntry(
            self.page_input_frame, textvariable=self.v_page,
            placeholder_text=t("ph_page_name"),
            fg_color=BG_INPUT, border_color="green",
            text_color=T_PRI, font=FL, width=200, corner_radius=6)
        self._page_entry_full.pack(side="left", pady=10)
        self._page_entry_full.bind("<Return>", lambda e: self._submit_page())
        self._btn_submit_page = ctk.CTkButton(
            self.page_input_frame, text=t("btn_send"),
            font=FL, height=32, width=90,
            fg_color="green", hover_color="#145c30",
            text_color=BG_MAIN, corner_radius=6,
            command=self._submit_page)
        self._btn_submit_page.pack(side="left", padx=10, pady=10)

        self.ow_frame = ctk.CTkFrame(p, fg_color="#FEF6E4",
                                      corner_radius=0, height=50)
        self.ow_frame.grid(row=3, column=0, sticky="ew")
        self.ow_frame.grid_propagate(False)
        self.ow_frame.grid_remove()
        p.rowconfigure(3, weight=0)
        self.ow_label = ctk.CTkLabel(self.ow_frame, text="",
                                      font=FL, text_color="#8C6A10")
        self.ow_label.pack(side="left", padx=(14, 12), pady=10)
        self._btn_ow_yes = ctk.CTkButton(
            self.ow_frame, text=t("btn_yes_overwrite"),
            font=FL, height=32, width=190,
            fg_color="#2D6A2D", hover_color="#1a5220",
            text_color="white", corner_radius=6,
            command=lambda: self._submit_overwrite(True))
        self._btn_ow_yes.pack(side="left", pady=10)
        self._btn_ow_no = ctk.CTkButton(
            self.ow_frame, text=t("btn_no_cancel"),
            font=FL, height=32, width=150,
            fg_color="#A32020", hover_color="#7B1515",
            text_color="white", corner_radius=6,
            command=lambda: self._submit_overwrite(False))
        self._btn_ow_no.pack(side="left", padx=(8, 0), pady=10)

    # ── Platform toggle ───────────────────────────────────────────────────────
    def _toggle_platform(self, pf, init=False):
        self.v_platform.set(pf)
        if pf == "ios":
            self._btn_plat_ios.configure(fg_color=ACCENT_IOS, text_color=BG_MAIN,
                                          hover_color=ACCENT_IOS_DK)
            self._btn_plat_and.configure(fg_color=BG_INPUT, text_color=T_MUT,
                                          hover_color="#E8E0D0")
            if not init:
                self.ios_hdr.pack(fill="x", padx=14, pady=3)
                self.ios_panel.pack(fill="x", pady=(0, 6))
            self.and_hdr.pack_forget()
            self.and_panel.pack_forget()
            self.bl_hdr.pack_forget()
            self.bl_frame.pack_forget()
        else:
            self._btn_plat_and.configure(fg_color=ACCENT_DK, text_color=BG_MAIN,
                                          hover_color=ACCENT_DK)
            self._btn_plat_ios.configure(fg_color=BG_INPUT, text_color=T_MUT,
                                          hover_color="#E8E0D0")
            self.ios_hdr.pack_forget()
            self.ios_panel.pack_forget()
            if not init:
                self.and_hdr.pack(fill="x", padx=14, pady=3)
                self.and_panel.pack(fill="x", pady=(0, 6))
                self.bl_hdr.pack(fill="x", padx=14, pady=3)
                self.bl_frame.pack(fill="x", padx=14, pady=(0, 10))
        self._upd_label()

    def _ios_changed(self, profiles, active):
        self.cfg["ios_profiles"] = profiles
        self.cfg["active_ios_profile"] = active
        self._upd_label()

    def _and_changed(self, profiles, active):
        self.cfg["android_profiles"] = profiles
        self.cfg["active_android_profile"] = active
        self._upd_label()

    def _upd_label(self):
        pf = self.v_platform.get()
        if pf == "ios":
            self.lbl_prof.configure(
                text=f"iOS  |  {self.ios_panel.get_active()}", text_color=ACCENT_IOS)
        else:
            self.lbl_prof.configure(
                text=f"Android  |  {self.and_panel.get_active()}", text_color=ACCENT)

    # ── Log yardımcıları ──────────────────────────────────────────────────────
    def _log(self, text, tag=""):
        def _d():
            self.log_box.configure(state="normal")
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_box._textbox.insert("end", f"[{ts}] {text}\n", tag or "")
            self.log_box._textbox.see("end")
            self.log_box.configure(state="disabled")
        self.after(0, _d)

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _classify(self, line):
        l = line.lower()
        if any(k in l for k in ("kaydedildi", "tamamlandi", "saved", "completed", "done")): return "ok"
        if any(k in l for k in ("hata", "error", "traceback", "exception", "failed")): return "err"
        if any(k in l for k in ("warning", "uyar")): return "warn"
        if any(k in l for k in ("driver", "appium", "baslatilyior", "baslatil", "starting")): return "info"
        return ""

    # ── Config toplama / doğrulama ────────────────────────────────────────────
    def _collect(self):
        secs = [k for k, v in [("unique",    self.v_sec_unique),
                                 ("undefined", self.v_sec_undefined),
                                 ("duplicate", self.v_sec_duplicate),
                                 ("missing",   self.v_sec_missing)] if v.get()]
        bl = [x.strip() for x in self.v_blacklist.get().split(",") if x.strip()]
        return {
            "platform":               self.v_platform.get(),
            "language":               get_lang(),
            "output_word":            self.v_out_word.get(),
            "output_excel":           self.v_out_excel.get(),
            "output_json":            self.v_out_json.get(),
            "output_dir":             self.v_out_dir.get(),
            "appium_server":          self.v_appium.get(),
            "document_sections":      secs,
            "blacklist_ids":          bl,
            "ios_profiles":           self.ios_panel.get_all(),
            "active_ios_profile":     self.ios_panel.get_active(),
            "android_profiles":       self.and_panel.get_all(),
            "active_android_profile": self.and_panel.get_active(),
        }

    def _validate(self, cfg):
        if not cfg["output_dir"]:        return t("val_output_dir_empty")
        if not cfg["document_sections"]: return t("val_no_sections")
        if not any([cfg["output_word"], cfg["output_excel"], cfg["output_json"]]):
            return t("val_no_output_fmt")
        if cfg["platform"] == "ios":
            if not cfg["ios_profiles"].get(
                    cfg["active_ios_profile"], {}).get("bundle_id"):
                return t("val_ios_bundle_empty")
        else:
            if not cfg["android_profiles"].get(
                    cfg["active_android_profile"], {}).get("app_package"):
                return t("val_and_pkg_empty")
        return None

    def _set_busy(self, busy):
        if busy:
            self.btn_run.configure(state="disabled", fg_color="#D8D0C0",
                                   text_color="#8C7D6A")
            self.btn_smart_connect.configure(state="disabled", fg_color="#D8D0C0",
                                              text_color="#8C7D6A")
            self.btn_stop.configure(state="normal")
            self.btn_summary.configure(state="disabled")
            self.badge.set("running")
        else:
            self.btn_run.configure(state="normal", fg_color="#1a8242",
                                   hover_color="#145c30", text_color="#FFFFFF")
            self.btn_smart_connect.configure(state="normal", fg_color=ACCENT_IOS,
                                              hover_color=ACCENT_IOS_DK,
                                              text_color="#FFFFFF")
            self.btn_stop.configure(state="disabled")
            self.btn_summary.configure(state="normal")

    def _pick_excel(self):
        path = filedialog.askopenfilename(
            title=t("lbl_excel"),
            filetypes=[("Excel", "*.xlsx *.xls"), ("All", "*.*")],
            initialdir=self.v_out_dir.get() or _BASE)
        if path:
            self.v_summary_xl.set(path)

    # ── Checker çalıştır ──────────────────────────────────────────────────────
    def _run_checker(self):
        cfg = self._collect()
        err = self._validate(cfg)
        if err:
            messagebox.showerror(t("msg_missing_info"), err)
            return

        save_config(cfg)
        self.cfg = cfg
        write_config_py(cfg, os.path.join(_BASE, "config.py"))

        platform = cfg["platform"]
        script   = ("element_checker_ios.py" if platform == "ios"
                    else "element_checker_android.py")
        spath    = os.path.join(_BASE, script)
        if not os.path.exists(spath):
            messagebox.showerror(t("msg_error_title"),
                                  t("msg_script_not_found", path=spath))
            return

        self._clear_log()
        active  = cfg[f"active_{platform}_profile"]
        fmt_str = _build_output_format(cfg)
        self._log(t("log_platform", platform=platform.upper(),
                     profile=active, fmt=fmt_str), "info")
        self._log(t("log_separator"), "dim")
        self._set_busy(True)
        self._pn_ev.clear()
        self.page_input_frame.grid_remove()

        threading.Thread(
            target=self._stream,
            args=([sys.executable, spath], _BASE, self._done_checker),
            daemon=True).start()

    def _show_page_input(self):
        self.v_page.set("")
        self.page_input_frame.grid(row=2, column=0, sticky="ew")
        for w in self.page_input_frame.winfo_children():
            if isinstance(w, ctk.CTkEntry):
                w.focus_set()
                break

    def _hide_page_input(self):
        self.page_input_frame.grid_remove()

    def _submit_page(self):
        name = self.v_page.get().strip()
        if not name:
            self._log(t("msg_page_empty"), "warn")
            return
        self._pn_ans = name
        self._pn_ev.set()

    def _show_overwrite(self, label_text):
        self.ow_label.configure(text=t("msg_overwrite_q", label=label_text))
        self.ow_frame.grid(row=3, column=0, sticky="ew")

    def _hide_overwrite(self):
        self.ow_frame.grid_remove()

    def _submit_overwrite(self, yes: bool):
        self._ow_ans = yes
        self._ow_ev.set()

    # ── Build Summary çalıştır ────────────────────────────────────────────────
    def _run_summary(self):
        xl = self.v_summary_xl.get().strip()
        if not xl:
            messagebox.showwarning(t("msg_warn_title"), t("msg_excel_select"))
            return
        if not os.path.exists(xl):
            messagebox.showerror(t("msg_error_title"),
                                  t("msg_file_not_found", path=xl))
            return

        spath = os.path.join(_BASE, "build_summary.py")
        if not os.path.exists(spath):
            messagebox.showerror(t("msg_error_title"),
                                  t("msg_script_not_found", path=spath))
            return

        cfg = self._collect()
        save_config(cfg)
        self.cfg = cfg

        self._clear_log()
        self._log(t("log_excel_file", name=os.path.basename(xl)), "info")
        self._log(t("log_summary_start"), "info")
        self._log(t("log_separator"), "dim")
        self._set_busy(True)

        threading.Thread(
            target=self._stream,
            args=([sys.executable, spath], _BASE, self._done_summary),
            kwargs={"xl_override": xl},
            daemon=True).start()

    # ── Subprocess stream ──────────────────────────────────────────────────────
    def _stream(self, cmd, cwd, done_cb, xl_override=None):
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        if xl_override:
            env["WIMID_EXCEL_FILE"] = xl_override

        try:
            self._proc = subprocess.Popen(
                [cmd[0], "-u"] + cmd[1:], cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE, text=True, encoding="utf-8",
                errors="replace", bufsize=0, env=env,
            )
            buf = ""
            page_asked = False

            def _normalize(s):
                return s.replace("\u0131", "i").replace("\u0130", "i").lower()

            def _is_page_prompt(text):
                n = _normalize(text)
                return "sayfa adi gir" in n or ("sayfa ad" in n and "gir" in n)

            def handle(line):
                nonlocal page_asked
                low  = line.lower()
                norm = _normalize(line)

                if not page_asked and _is_page_prompt(line):
                    page_asked = True
                    self._log(line, "warn")
                    self.after(0, self._show_page_input)
                    self._pn_ev.clear()
                    self._pn_ev.wait(timeout=120)
                    answer = self._pn_ans
                    self.after(0, self._hide_page_input)
                    self._log(t("log_page_answer", name=answer), "info")
                    self._proc.stdin.write(answer + "\n")
                    self._proc.stdin.flush()
                    return

                if "uezerine yazmak istiyor musunuz" in norm or "[e/h]" in low:
                    import re as _re
                    m = _re.search(r"'([^']+)'", line)
                    short = m.group(1) if m else line
                    short = short[:60] + ("..." if len(short) > 60 else "")
                    self.after(0, lambda s=short: self._show_overwrite(s))
                    self._ow_ev.clear()
                    self._ow_ev.wait(timeout=60)
                    answer = "e" if self._ow_ans else "h"
                    self.after(0, self._hide_overwrite)
                    self._proc.stdin.write(answer + "\n")
                    self._proc.stdin.flush()
                    self._log(t("log_overwrite_yes") if self._ow_ans
                               else t("log_overwrite_no"),
                               "info" if self._ow_ans else "warn")
                    return

                self._log(line, self._classify(line))

            while True:
                ch = self._proc.stdout.read(1)
                if ch == "":
                    break
                if ch == "\n":
                    line = buf.rstrip()
                    buf  = ""
                    if line:
                        handle(line)
                else:
                    buf += ch
                    if not page_asked:
                        nb = _normalize(buf)
                        if "sayfa adi gir" in nb:
                            handle(buf.strip())
                            buf = ""
                    if "[e/h]:" in buf.lower():
                        handle(buf.strip())
                        buf = ""

            if buf.strip():
                self._log(buf.strip(), self._classify(buf))

            self._proc.wait()
            done_cb(self._proc.returncode)

        except Exception as ex:
            self._log(f"ERROR: {ex}", "err")
            self.after(0, lambda: done_cb(-1))
        finally:
            self._proc = None

    def _done_checker(self, rc):
        self.after(0, lambda: self._set_busy(False))
        self._log(t("log_separator"), "dim")
        if rc == 0:
            self._log(t("log_script_ok"), "ok")
            self.after(0, lambda: self.badge.set("ok"))
        else:
            self._log(t("log_script_fail", rc=rc), "err")
            self.after(0, lambda: self.badge.set("error"))

    def _done_summary(self, rc):
        self.after(0, lambda: self._set_busy(False))
        self._log(t("log_separator"), "dim")
        if rc == 0:
            self._log(t("log_summary_ok"), "ok")
            self.after(0, lambda: self.badge.set("ok"))
        else:
            self._log(t("log_summary_fail", rc=rc), "err")
            self.after(0, lambda: self.badge.set("error"))

    def _stop_proc(self):
        if self._proc:
            self._proc.terminate()
            self._log(t("log_process_stopped"), "warn")
        if hasattr(self, '_smart_tab_ref') and self._smart_tab_ref:
            self._smart_tab_ref.stop()
        if hasattr(self, '_session_ref') and self._session_ref:
            self._session_ref.abort_session()
        self._set_busy(False)
        self.badge.set("idle")
        self._pn_ev.set()
        self._ow_ev.set()
        self.after(0, self._hide_page_input)
        self.after(0, self._hide_overwrite)

    def on_close(self):
        if self._proc:
            self._proc.terminate()
        if hasattr(self, '_session_ref') and self._session_ref:
            self._session_ref.abort_session()
        save_config(self._collect())
        self.destroy()


# ════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()