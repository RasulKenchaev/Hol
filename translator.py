"""
Мувофиқати ақиб — ҳамаи функсияҳо акнун аз db.py кор мекунанд.
"""
import db


def load_data() -> dict:
    return db.load_data()


def normalize(text: str) -> str:
    return text.strip().lower()


def translate_phrase(text: str, dialect_key: str, data: dict = None) -> str:
    return db.translate_phrase(text, dialect_key)


def get_all_dialects(data: dict = None) -> dict:
    return {d["key"]: d["name"] for d in db.get_dialects()}


def translate_to_all(text: str, data: dict = None) -> dict:
    return {d["key"]: db.translate_phrase(text, d["key"])
            for d in db.get_dialects()}
