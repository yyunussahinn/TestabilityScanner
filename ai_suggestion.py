"""
ai_suggestion.py
────────────────
Element taramasında AI Suggestion sütunu için Claude API'yi kullanır.
"""


import json
import re
import ssl
import urllib.request
import urllib.error
from i18n import t
from constants import STATUS_UNIQUE, STATUS_DUPLICATE, STATUS_MISSING, STATUS_UNDEFINED

# ══════════════════════════════════════════════════════
# ▼▼▼  API KEY BURAYA  ▼▼▼
API_KEY = "sk-ant-api03-BURAYA_YAPISTIR"
# ▲▲▲  API KEY BURAYA  ▲▲▲
# ══════════════════════════════════════════════════════

API_URL = "https://api.anthropic.com/v1/messages"
MODEL   = "claude-sonnet-4-20250514"

HEADERS = {
    "Content-Type": "application/json",
    "anthropic-version": "2023-06-01",
    "x-api-key": API_KEY,
}

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode    = ssl.CERT_NONE

_TYPE_SUFFIX = {
    "edittext":       ("textbox",          "Textbox"),
    "button":         ("btn",              "Btn"),
    "imagebutton":    ("btn",              "Btn"),
    "checkbox":       ("checkbox",         "Checkbox"),
    "radiobutton":    ("radio_btn",        "RadioBtn"),
    "switch":         ("toggle",           "Toggle"),
    "spinner":        ("dropdown",         "Dropdown"),
    "textview":       ("label",            "Label"),
    "imageview":      ("icon",             "Icon"),
    "framelayout":    ("container",        "Container"),
    "linearlayout":   ("container",        "Container"),
    "relativelayout": ("container",        "Container"),
    "viewgroup":      ("container",        "Container"),
    "view":           ("container",        "Container"),
    "textfield":      ("textbox",          "Textbox"),
    "securetextfield":("password_textbox", "PasswordTextbox"),
    "cell":           ("cell",             "Cell"),
    "other":          ("view",             "View"),
}

def _type_hints(elem_type: str) -> tuple[str, str]:
    key = elem_type.lower().replace(".", "").replace("_", "")
    return _TYPE_SUFFIX.get(key, ("element", "Element"))


def _call_api(system_prompt: str, user_prompt: str, max_tokens: int = 300) -> str:
    body = json.dumps({
        "model":      MODEL,
        "max_tokens": max_tokens,
        "system":     system_prompt,
        "messages":   [{"role": "user", "content": user_prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(API_URL, data=body, headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20, context=_SSL_CTX) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for block in data.get("content", []):
                if block.get("type") == "text":
                    return block["text"].strip()
    except Exception as e:
        print(f"   {t('ai_api_error', error=e)}")
    return ""


def _acc_id_to_camel(acc_id: str) -> str:
    raw_parts = re.split(r"[_\-\.\s/]+", acc_id)
    result = []
    for i, part in enumerate(raw_parts):
        if not part:
            continue
        if i == 0:
            result.append(part[0].lower() + part[1:])
        else:
            result.append(part[0].upper() + part[1:])
    return "".join(result) or "element"


def _build_key(acc_id: str, elem_type: str) -> str:
    _, camel_sfx = _type_hints(elem_type)
    base = _acc_id_to_camel(acc_id)
    if base.lower().endswith(camel_sfx.lower()):
        return base
    return base + camel_sfx


def generate_json_suggestion(element: dict, platform: str) -> str:
    acc_id = element.get("acc_id", "")
    etype  = element.get("type", "")
    key    = _build_key(acc_id, etype)
    return json.dumps({
        "key":           key,
        "androidValue":  acc_id,
        "androidType":   "id",
        "iosValue":      acc_id,
        "iosType":       "accessibilityId",
    }, ensure_ascii=False, indent=2)


_SYS_ID = """You are a mobile accessibility ID naming expert.
Given a UI element without a proper accessibility ID and a list of existing IDs in the same app,
suggest a single snake_case accessibility ID.

Rules:
- MUST reflect BOTH the element's semantic purpose (label/text) AND its UI type.
- Type suffix rules (MANDATORY):
    EditText / TextField           -> _textbox
    SecureTextField                -> _password_textbox
    Button / ImageButton           -> _btn
    CheckBox                       -> _checkbox
    RadioButton                    -> _radio_btn
    Switch                         -> _toggle
    Spinner / Dropdown             -> _dropdown
    Cell                           -> _cell
    TextView / Label               -> _label
    ImageView / Icon               -> _icon
    ViewGroup / View / Container   -> _container
- Analyse existing IDs for naming prefix pattern and follow it.
- Return ONLY the suggested ID string, nothing else."""


def generate_id_suggestion(element: dict, existing_ids: list[str]) -> str:
    label     = element.get("label", "")
    value     = element.get("value", "")
    etype     = element.get("type", "")
    acc_id    = element.get("acc_id", "")
    page      = element.get("page", "")
    snake_sfx, _ = _type_hints(etype)

    user_prompt = (
        f"Screen/Page context: {page}\n"
        f"Element type: {etype}  ->  ID MUST end with '_{snake_sfx}'\n"
        f"Label/Text: {label}\n"
        f"Value: {value}\n"
        f"Current ID (if any): {acc_id}\n\n"
        f"Existing IDs in the app:\n"
        + "\n".join(f"  - {i}" for i in existing_ids[:30])
    )

    raw = _call_api(_SYS_ID, user_prompt, max_tokens=60)
    if raw:
        suggestion = raw.splitlines()[0].strip().strip('"').strip("'")
        suggestion = re.sub(r"\s+", "_", suggestion).lower()
        return suggestion

    base = _to_snake(label or value or etype or "element")
    return f"{base}_{snake_sfx}"


def _to_snake(text: str) -> str:
    words = re.sub(r"[^a-zA-Z0-9]+", " ", text).strip().split()
    return "_".join(w.lower() for w in words) or "element"


def enrich_elements(elements: list[dict], platform: str) -> list[dict]:
    existing_ids = [
        e["acc_id"] for e in elements
        if e.get("status") == STATUS_UNIQUE and e.get("acc_id")
    ]

    total = len(elements)
    print(t("shared_ai_start", total=total))

    for idx, elem in enumerate(elements, 1):
        status = elem.get("status", STATUS_MISSING)
        label  = elem.get("label") or elem.get("value") or elem.get("acc_id") or "?"
        etype  = elem.get("type", "")
        print(f"   [{idx:3d}/{total}] {status:15s} | {etype:15s} | {label[:35]}",
              end="", flush=True)

        try:
            if status == STATUS_UNIQUE:
                suggestion = generate_json_suggestion(elem, platform)
            else:
                suggestion = generate_id_suggestion(elem, existing_ids)
        except Exception as ex:
            suggestion = f"({t('ai_error_short', error=ex)})"

        elem["ai_suggestion"] = suggestion
        print(" ✓")

    print(t("shared_ai_done"))
    return elements