"""
smart_checker.py — v4.4  (i18n)
────────────────────────────────────────────────────────────────
Tüm log ve hata mesajları i18n.t() üzerinden yönetilir.
"""

import config as cfg
BLACKLIST = set(cfg.BLACKLIST_IDS)

import time
import os
from datetime import datetime
from collections import Counter
from i18n import t

IOS_ALWAYS = [
    "XCUIElementTypeTextField",
    "XCUIElementTypeSecureTextField",
    "XCUIElementTypeButton",
    "XCUIElementTypeCell",
]
IOS_CONDITIONAL = ["XCUIElementTypeOther"]

AND_ALWAYS = [
    "android.widget.EditText",
    "android.widget.Button",
    "android.widget.ImageButton",
    "android.widget.CheckBox",
    "android.widget.RadioButton",
    "android.widget.Switch",
    "android.widget.Spinner",
]
AND_CONDITIONAL = [
    "android.view.View",
    "android.view.ViewGroup",
    "android.widget.RelativeLayout",
    "android.widget.ImageView",
]
AND_RESOURCE_ONLY = ["android.widget.TextView"]

STATUS_UNIQUE    = "ID Var"
STATUS_DUPLICATE = "Duplicate"
STATUS_MISSING   = "ID Yok"
STATUS_UNDEFINED = "Undefined ID"


def get_new_status(status: str) -> str:
    return "" if status == STATUS_UNIQUE else "ID Eklenecek (Waiting Dev)"


# ════════════════════════════════════════════════════════════════════════════
#  APPIUM BAĞLANTI & ELEMENT TOPLAMA
# ════════════════════════════════════════════════════════════════════════════

def connect_and_capture(platform: str, profile: dict,
                         appium_server: str, screenshot_path: str,
                         log_cb=print) -> tuple[list, str]:
    from appium import webdriver

    log_cb(t("smart_checker_app_start"))

    if platform == "ios":
        from appium.options.ios import XCUITestOptions
        options = XCUITestOptions()
        options.platform_name    = "iOS"
        options.device_name      = profile["device_name"]
        options.platform_version = profile["platform_version"]
        options.automation_name  = "XCUITest"
        options.bundle_id        = profile["bundle_id"]
        options.no_reset         = profile.get("no_reset", True)
        options.udid             = profile["udid"]
    else:
        from appium.options.android import UiAutomator2Options
        options = UiAutomator2Options()
        options.platform_name    = "Android"
        options.device_name      = profile["device_name"]
        options.platform_version = profile["platform_version"]
        options.automation_name  = "UiAutomator2"
        options.app_package      = profile["app_package"]
        options.app_activity     = profile["app_activity"]
        options.no_reset         = profile.get("no_reset", True)

    driver = webdriver.Remote(appium_server, options=options)
    time.sleep(3)

    log_cb(t("smart_checker_screenshot"))
    os.makedirs(os.path.dirname(os.path.abspath(screenshot_path)), exist_ok=True)
    driver.get_screenshot_as_file(screenshot_path)
    log_cb(t("smart_checker_arrow", path=screenshot_path))

    detected_page = _get_detected_page(driver, platform)
    log_cb(t("smart_checker_page", page=detected_page or "(not found)"))

    pixel_ratio = 1.0
    if platform == "ios":
        try:
            from PIL import Image as PILImage
            with PILImage.open(screenshot_path) as img:
                ss_w, ss_h = img.size
            window = driver.get_window_size()
            pt_w   = window.get("width", ss_w)
            pt_h   = window.get("height", ss_h)
            pixel_ratio = ss_w / pt_w if pt_w > 0 else 1.0
            log_cb(t("smart_checker_screen_info",
                      ss_w=ss_w, ss_h=ss_h,
                      pt_w=pt_w, pt_h=pt_h,
                      ratio=pixel_ratio))
        except Exception as e:
            log_cb(t("smart_checker_ratio_error", error=e))
            pixel_ratio = 1.0

    log_cb(t("smart_checker_scanning"))
    screen_size = driver.get_window_size()
    sw = screen_size["width"]
    sh = screen_size["height"]

    all_elements = _collect_elements(driver, platform, detected_page,
                                      sw, sh, pixel_ratio, log_cb)

    driver.quit()
    log_cb(t("smart_checker_connected"))

    counts = Counter(e["status"] for e in all_elements)
    log_cb(t("smart_checker_sep"))
    log_cb(t("smart_checker_unique",    n=counts[STATUS_UNIQUE]))
    log_cb(t("smart_checker_undefined", n=counts[STATUS_UNDEFINED]))
    log_cb(t("smart_checker_duplicate", n=counts[STATUS_DUPLICATE]))
    log_cb(t("smart_checker_missing",   n=counts[STATUS_MISSING]))
    log_cb(t("smart_checker_sep"))

    return all_elements, detected_page


def _get_detected_page(driver, platform: str) -> str:
    try:
        if platform == "ios":
            import xml.etree.ElementTree as ET
            root = ET.fromstring(driver.page_source)
            for tag in ["XCUIElementTypeNavigationBar", "XCUIElementTypeStaticText"]:
                el = root.find(f".//{tag}")
                if el is not None:
                    lbl = el.get("label") or el.get("name") or ""
                    if lbl:
                        return lbl
        else:
            activity = driver.current_activity or ""
            return activity.split(".")[-1] if activity else ""
    except Exception:
        pass
    return ""


def _collect_elements(driver, platform: str, detected_page: str,
                       sw: int, sh: int, pixel_ratio: float, log_cb) -> list:
    candidates   = []
    all_elements = []

    if platform == "ios":
        all_elements, candidates = _collect_ios(driver, detected_page,
                                                 sw, sh, pixel_ratio)
    else:
        all_elements, candidates = _collect_android(driver, detected_page)

    name_counts = Counter(r["acc_id"] for r in candidates)
    for row in candidates:
        row["status"] = (STATUS_UNIQUE
                         if name_counts[row["acc_id"]] == 1
                         else STATUS_DUPLICATE)
        all_elements.append(row)

    with_rect    = sum(1 for e in all_elements if e.get("rect"))
    without_rect = sum(1 for e in all_elements if not e.get("rect"))
    log_cb(t("smart_checker_rect_info",
              with_rect=with_rect, without_rect=without_rect))

    return all_elements


def _get_ios_rect(el, pixel_ratio: float = 1.0) -> dict | None:
    try:
        loc = el.location
        siz = el.size
        if siz.get("width", 0) > 0 and siz.get("height", 0) > 0:
            return {
                "x":      int(loc["x"]      * pixel_ratio),
                "y":      int(loc["y"]      * pixel_ratio),
                "width":  int(siz["width"]  * pixel_ratio),
                "height": int(siz["height"] * pixel_ratio),
            }
    except Exception:
        pass

    try:
        r = el.rect
        if r and r.get("width", 0) > 0 and r.get("height", 0) > 0:
            return {
                "x":      int(r["x"]      * pixel_ratio),
                "y":      int(r["y"]      * pixel_ratio),
                "width":  int(r["width"]  * pixel_ratio),
                "height": int(r["height"] * pixel_ratio),
            }
    except Exception:
        pass

    return None


def _collect_ios(driver, detected_page, sw, sh, pixel_ratio):
    from appium.webdriver.common.appiumby import AppiumBy as AB

    def get_name(el):  return el.get_attribute("name")  or ""
    def get_label(el): return el.get_attribute("label") or ""
    def get_value(el): return el.get_attribute("value") or ""
    def short_type(t_): return t_.replace("XCUIElementType", "")

    def is_visible(el):
        try:
            r = el.rect
            w, h = r.get("width", 0), r.get("height", 0)
            x = r.get("x", 0)
            return w > 0 and h > 0 and x < sw and (x + w) > 0
        except Exception:
            return False

    def find_by_acc(name):
        try:
            driver.find_element(AB.ACCESSIBILITY_ID, name)
            return True
        except Exception:
            return False

    def has_real_id(name, label):
        return (name and name != label
                and not name.startswith("__")
                and find_by_acc(name))

    def is_undefined(name):
        return "undefined" in name.lower() or name.startswith("__")

    all_elems  = []
    candidates = []

    for etype in IOS_ALWAYS + IOS_CONDITIONAL:
        elems = driver.find_elements(AB.XPATH, f"//{etype}")
        for el in elems:
            if etype in IOS_CONDITIONAL:
                if el.get_attribute("accessible") != "true":
                    continue
            if not is_visible(el):
                continue

            name    = get_name(el)
            label   = get_label(el)
            value   = get_value(el)
            display = label or value or ""
            stype   = short_type(etype)
            rect    = _get_ios_rect(el, pixel_ratio)

            if has_real_id(name, label):
                entry = {"page": detected_page, "type": stype,
                         "label": display, "value": value,
                         "acc_id": name, "rect": rect}
                if is_undefined(name):
                    entry["status"] = STATUS_UNDEFINED
                    all_elems.append(entry)
                else:
                    candidates.append(entry)
            else:
                all_elems.append({"page": detected_page, "type": stype,
                                   "label": display, "value": value,
                                   "acc_id": "", "status": STATUS_MISSING,
                                   "rect": rect})

    return all_elems, candidates


def _collect_android(driver, detected_page):
    from appium.webdriver.common.appiumby import AppiumBy as AB

    def short_type(t_): return t_.split(".")[-1]
    def clean(v):
        s = (v or "").strip()
        return "" if s.lower() in ("null", "none") else s

    def get_rid(el):
        rid = clean(el.get_attribute("resource-id"))
        if not rid:
            return ""
        return rid.split("/")[-1] if "/" in rid else rid

    def get_label(el):
        return (clean(el.get_attribute("content-desc"))
                or clean(el.get_attribute("text")))

    def get_value(el):
        return clean(el.get_attribute("text"))

    def is_undefined(rid):
        return "undefined" in rid.lower()

    def is_interactive(el, etype):
        if etype in AND_ALWAYS:
            return True
        if etype in AND_RESOURCE_ONLY:
            return bool(get_rid(el))
        if etype in AND_CONDITIONAL:
            return (el.get_attribute("clickable") == "true"
                    or bool(get_rid(el)))
        return False

    def get_rect(el):
        try:
            r = el.rect
            return {"x": r["x"], "y": r["y"],
                    "width": r["width"], "height": r["height"]}
        except Exception:
            return None

    all_elems  = []
    candidates = []
    ALL_TYPES  = AND_ALWAYS + AND_CONDITIONAL + AND_RESOURCE_ONLY

    for etype in ALL_TYPES:
        elems = driver.find_elements(AB.XPATH, f"//{etype}")
        for el in elems:
            try:
                if not is_interactive(el, etype):
                    continue
                rid   = get_rid(el)
                label = get_label(el)
                value = get_value(el)
                stype = short_type(etype)
                rect  = get_rect(el)
            except Exception:
                continue

            if not rid and not label and not value:
                continue

            if rid:
                if rid in BLACKLIST or (rid.startswith("__") and rid.endswith("__")):
                    continue
                entry = {"page": detected_page, "type": stype,
                         "label": label, "value": value,
                         "acc_id": rid, "rect": rect}
                if is_undefined(rid):
                    entry["status"] = STATUS_UNDEFINED
                    all_elems.append(entry)
                else:
                    candidates.append(entry)
            else:
                all_elems.append({"page": detected_page, "type": stype,
                                   "label": label, "value": value,
                                   "acc_id": "", "status": STATUS_MISSING,
                                   "rect": rect})

    return all_elems, candidates


# ════════════════════════════════════════════════════════════════════════════
#  RAPOR ÜRETIMI
# ════════════════════════════════════════════════════════════════════════════

def generate_reports(
    elements:          list,
    page_name:         str,
    output_dir:        str,
    platform:          str,
    screenshot_path:   str,
    output_fmt:        str,
    document_sections: list = None,
    log_cb=print,
):
    import shared as sh

    os.makedirs(output_dir, exist_ok=True)

    if document_sections is None:
        document_sections = ["unique", "undefined", "duplicate", "missing"]

    plat_suffix = "IOS" if platform == "ios" else "Android"

    word_file  = os.path.join(output_dir, f"{page_name}_smart_{plat_suffix}.docx")
    excel_file = os.path.join(output_dir, f"Smart_Report_{plat_suffix}.xlsx")
    json_file  = os.path.join(output_dir, f"{page_name}_smart_{platform}.json")

    fmt_parts = set(output_fmt.split("+"))

    if "word" in fmt_parts:
        try:
            sh.generate_word(
                all_elements=elements, page_name=page_name, word_file=word_file,
                document_sections=document_sections, platform=platform,
                screenshot_path=screenshot_path)
            log_cb(t("smart_checker_word_saved", file=word_file))
        except Exception as ex:
            log_cb(t("smart_checker_word_error", error=ex))

    if "excel" in fmt_parts:
        try:
            sh.generate_excel(
                all_elements=elements, page_name=page_name, excel_file=excel_file,
                document_sections=document_sections, platform=platform,
                screenshot_path=screenshot_path)
            log_cb(t("smart_checker_excel_saved", file=excel_file))
        except Exception as ex:
            log_cb(t("smart_checker_excel_error", error=ex))

    if "json" in fmt_parts:
        try:
            sh.generate_json(
                elements=elements, page_name=page_name,
                json_file=json_file, platform=platform)
            log_cb(t("smart_checker_json_saved", file=json_file))
        except Exception as ex:
            log_cb(t("smart_checker_json_error", error=ex))