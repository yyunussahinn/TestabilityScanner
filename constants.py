"""
constants.py — Where is My Id
────────────────────────────────────────────────────────────────
Merkezi durum (status) sabitleri.

Daha önce STATUS_UNIQUE / STATUS_DUPLICATE / STATUS_MISSING /
STATUS_UNDEFINED değerleri shared.py, smart_checker.py, ai_suggestion.py
içinde birbirinden bağımsız olarak tanımlanıyor, session_tab.py ise
bunları hiç sabit kullanmadan doğrudan string literal olarak yazıyordu.

Artık TEK doğruluk kaynağı burasıdır. Diğer tüm modüller bu dosyadan
import eder:

    from constants import STATUS_UNIQUE, STATUS_DUPLICATE, \
        STATUS_MISSING, STATUS_UNDEFINED, NS_WAITING, ALL_STATUSES, \
        SECTION_TO_STATUS, get_new_status

Bu dosyanın hiçbir bağımlılığı yoktur (leaf module) — bu sayede
shared.py <-> ai_suggestion.py arasında var olan circular import riski
de ortadan kalkar; lazy import'a ihtiyaç duymadan üstte import edilebilir.
"""

STATUS_UNIQUE    = "Unique ID"
STATUS_DUPLICATE = "Duplicate ID"
STATUS_MISSING   = "Missing ID"
STATUS_UNDEFINED = "Undefined ID"

ALL_STATUSES = [STATUS_MISSING, STATUS_UNDEFINED, STATUS_DUPLICATE, STATUS_UNIQUE]

NS_WAITING = "ID Must Be Added (Waiting Dev)"

SECTION_TO_STATUS: dict[str, str] = {
    "missing":   STATUS_MISSING,
    "undefined": STATUS_UNDEFINED,
    "duplicate": STATUS_DUPLICATE,
    "unique":    STATUS_UNIQUE,
}

# Rapor / tablo sıralaması için (session_tab.py'de kullanılır)
STATUS_ORDER: dict[str, int] = {
    STATUS_UNIQUE:    0,
    STATUS_UNDEFINED: 1,
    STATUS_DUPLICATE: 2,
    STATUS_MISSING:   3,
}


def get_new_status(status: str) -> str:
    """Unique ID dışındaki tüm statüler için 'New Status' değerini üretir."""
    return "" if status == STATUS_UNIQUE else NS_WAITING