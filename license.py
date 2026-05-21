"""
Модули литсензия.
Формати калид: LAHJA-XXXX-XXXX-XXXX-CCCCCC
  LAHJA  — префикси барнома
  XXXX   — 3 блоки рандом (12 ҳарф)
  CCCCCC — контролӣ HMAC-SHA256
"""
import os, json, hmac, hashlib, secrets, string

_DIR      = os.path.dirname(os.path.abspath(__file__))
_LIC_FILE = os.path.join(_DIR, ".license")
_SECRET   = b"TajikDialect@Lahja2024#LahjaHoiTojikiston"


def _checksum(code: str) -> str:
    return hmac.new(_SECRET, code.upper().encode(), hashlib.sha256).hexdigest()[:6].upper()


def generate_key() -> str:
    """Калиди нав тавлид мекунад."""
    chars = string.ascii_uppercase + string.digits
    code  = "".join(secrets.choice(chars) for _ in range(12))
    parts = [code[:4], code[4:8], code[8:12]]
    chk   = _checksum("-".join(parts))
    return f"LAHJA-{parts[0]}-{parts[1]}-{parts[2]}-{chk}"


def validate_key(key: str) -> bool:
    """Калидро санҷида мегирад."""
    parts = key.strip().upper().split("-")
    if len(parts) != 5 or parts[0] != "LAHJA":
        return False
    chk = _checksum("-".join(parts[1:4]))
    return parts[4] == chk


def is_activated() -> bool:
    """Оё барнома фаъол аст?"""
    try:
        with open(_LIC_FILE, encoding="utf-8") as f:
            return validate_key(json.load(f).get("key", ""))
    except Exception:
        return False


def activate(key: str) -> bool:
    """Калидро фаъол мекунад."""
    if validate_key(key):
        with open(_LIC_FILE, "w", encoding="utf-8") as f:
            json.dump({"key": key.strip().upper()}, f)
        return True
    return False


def get_key() -> str:
    """Калиди фаъоли ҳозираро бармегардонад."""
    try:
        with open(_LIC_FILE, encoding="utf-8") as f:
            return json.load(f).get("key", "")
    except Exception:
        return ""


def deactivate():
    """Литсензияро бекор мекунад."""
    try:
        os.remove(_LIC_FILE)
    except Exception:
        pass
