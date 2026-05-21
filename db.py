"""
Модули SQLite барои базаи лаҳҷаҳо.
Ҷои dialect_data.json + translator.py-и кӯҳнаро мегирад.
"""
import sqlite3
import os
import re

DB_FILE = os.path.join(os.path.dirname(__file__), "dialect_data.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Ҳамаи ҷадвалҳоро месозад (агар вуҷуд надошта бошанд)."""
    conn = get_connection()
    conn.executescript("""
        -- ══════════════════════════════════════════
        -- Ҷадвалҳои асосии мавҷуда
        -- ══════════════════════════════════════════

        CREATE TABLE IF NOT EXISTS dialects (
            key        TEXT PRIMARY KEY,
            name       TEXT NOT NULL,
            region     TEXT NOT NULL DEFAULT '',
            sort_order INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS words (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            dialect_key  TEXT NOT NULL REFERENCES dialects(key) ON DELETE CASCADE,
            literary     TEXT NOT NULL,
            dialect_form TEXT NOT NULL,
            category     TEXT NOT NULL DEFAULT 'words',
            pos          TEXT NOT NULL DEFAULT ''
        );

        -- ══════════════════════════════════════════
        -- Вилоятҳо (Провинсияҳо)
        -- ══════════════════════════════════════════
        CREATE TABLE IF NOT EXISTS provinces (
            key        TEXT PRIMARY KEY,
            name       TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0
        );

        -- ══════════════════════════════════════════
        -- Морфология: решаҳо
        -- ══════════════════════════════════════════
        CREATE TABLE IF NOT EXISTS roots (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            root    TEXT UNIQUE NOT NULL,
            pos     TEXT NOT NULL DEFAULT '',
            meaning TEXT DEFAULT '',
            notes   TEXT DEFAULT ''
        );

        -- ══════════════════════════════════════════
        -- Морфология: пешвандҳо
        -- ══════════════════════════════════════════
        CREATE TABLE IF NOT EXISTS prefixes (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            prefix   TEXT UNIQUE NOT NULL,
            meaning  TEXT DEFAULT '',
            category TEXT DEFAULT ''
        );

        -- ══════════════════════════════════════════
        -- Морфология: пасвандҳо
        -- ══════════════════════════════════════════
        CREATE TABLE IF NOT EXISTS suffixes (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            suffix   TEXT UNIQUE NOT NULL,
            meaning  TEXT DEFAULT '',
            category TEXT DEFAULT '',
            pos_from TEXT DEFAULT '',
            pos_to   TEXT DEFAULT ''
        );

        -- ══════════════════════════════════════════
        -- Шаклҳои феъл
        -- ══════════════════════════════════════════
        CREATE TABLE IF NOT EXISTS verb_forms (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            root_id      INTEGER REFERENCES roots(id) ON DELETE CASCADE,
            infinitive   TEXT UNIQUE NOT NULL,
            present_stem TEXT DEFAULT '',
            past_stem    TEXT DEFAULT '',
            verb_class   TEXT DEFAULT ''
        );

        -- ══════════════════════════════════════════
        -- Калимаҳои сермаъно
        -- ══════════════════════════════════════════
        CREATE TABLE IF NOT EXISTS polysemy (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            word        TEXT NOT NULL,
            meaning_num INTEGER NOT NULL DEFAULT 1,
            pos         TEXT DEFAULT '',
            meaning     TEXT NOT NULL,
            example     TEXT DEFAULT '',
            domain      TEXT DEFAULT ''
        );

        -- ══════════════════════════════════════════
        -- Индексҳо
        -- ══════════════════════════════════════════
        CREATE INDEX IF NOT EXISTS idx_words_lit
            ON words(lower(literary));
        CREATE INDEX IF NOT EXISTS idx_words_form
            ON words(lower(dialect_form));
        CREATE INDEX IF NOT EXISTS idx_words_dk
            ON words(dialect_key);
        CREATE INDEX IF NOT EXISTS idx_words_lit_dk
            ON words(lower(literary), dialect_key);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_polysemy_uniq
            ON polysemy(lower(word), meaning_num);
        CREATE INDEX IF NOT EXISTS idx_roots_root
            ON roots(lower(root));
        CREATE INDEX IF NOT EXISTS idx_vf_infinitive
            ON verb_forms(lower(infinitive));
    """)

    # Пайванди вилоят ба ноҳия — агар сутун нашудааст
    existing_cols = {r["name"] for r in conn.execute("PRAGMA table_info(dialects)")}
    if "province_key" not in existing_cols:
        conn.execute(
            "ALTER TABLE dialects ADD COLUMN province_key TEXT REFERENCES provinces(key)"
        )

    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# Хондан
# ══════════════════════════════════════════════════════════════════════════════

def get_dialects() -> list[dict]:
    """Феҳристи лаҳҷаҳо бо тартиб."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT key, name, region FROM dialects ORDER BY sort_order, rowid"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def init_users_db():
    """Ҷадвалҳои корбарон ва журнали дастрасӣ."""
    import hashlib
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL DEFAULT 'user',
            created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            last_login    TEXT
        );
        CREATE TABLE IF NOT EXISTS access_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
            action     TEXT NOT NULL,
            timestamp  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );
    """)
    # Суперадмини пешфарз (агар вуҷуд надошта бошад)
    h = hashlib.sha256("admin123".encode()).hexdigest()
    conn.execute("""INSERT OR IGNORE INTO users (username,password_hash,role)
                    VALUES ('admin',?,'admin')""", (h,))
    conn.commit()
    conn.close()


def verify_user(username: str, password: str):
    import hashlib
    h = hashlib.sha256(password.encode()).hexdigest()
    conn = get_connection()
    r = conn.execute(
        "SELECT id,username,role FROM users WHERE username=? AND password_hash=?",
        (username, h)
    ).fetchone()
    if r:
        conn.execute(
            "UPDATE users SET last_login=datetime('now','localtime') WHERE id=?",
            (r["id"],)
        )
        conn.commit()
    conn.close()
    return dict(r) if r else None


def register_user(username: str, password: str):
    import hashlib
    h = hashlib.sha256(password.encode()).hexdigest()
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username,password_hash) VALUES (?,?)",
            (username, h)
        )
        conn.commit()
        r = conn.execute(
            "SELECT id,username,role FROM users WHERE username=?", (username,)
        ).fetchone()
        conn.close()
        return dict(r)
    except Exception:
        conn.close()
        return None


def change_password(user_id: int, old_password: str, new_password: str) -> bool:
    import hashlib
    old_h = hashlib.sha256(old_password.encode()).hexdigest()
    new_h = hashlib.sha256(new_password.encode()).hexdigest()
    conn  = get_connection()
    r = conn.execute(
        "SELECT id FROM users WHERE id=? AND password_hash=?", (user_id, old_h)
    ).fetchone()
    if not r:
        conn.close()
        return False
    conn.execute("UPDATE users SET password_hash=? WHERE id=?", (new_h, user_id))
    conn.commit()
    conn.close()
    return True


def log_access(user_id: int, action: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO access_log (user_id,action) VALUES (?,?)",
        (user_id, action)
    )
    conn.commit()
    conn.close()


def get_user_stats() -> dict:
    conn = get_connection()
    users = conn.execute(
        "SELECT id,username,role,created_at,last_login FROM users ORDER BY id"
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    logins = conn.execute(
        "SELECT COUNT(*) as c FROM access_log WHERE action='login'"
    ).fetchone()["c"]
    per_user = conn.execute(
        """SELECT u.username, COUNT(l.id) as cnt
           FROM users u LEFT JOIN access_log l ON l.user_id=u.id AND l.action='login'
           GROUP BY u.id ORDER BY cnt DESC"""
    ).fetchall()
    conn.close()
    return {
        "users":       [dict(u) for u in users],
        "total_users": total,
        "total_logins": logins,
        "per_user":    [dict(r) for r in per_user],
    }


def load_data() -> dict:
    """
    Ба формати dict-и кӯҳна мебаргардад (мувофиқати ақиб).
    {dialects: {key: {name, region, words, phrases}}, word_pos: {}}
    """
    conn = get_connection()
    data: dict = {"dialects": {}, "word_pos": {}}

    for row in conn.execute(
        "SELECT key, name, region FROM dialects ORDER BY sort_order, rowid"
    ):
        data["dialects"][row["key"]] = {
            "name":    row["name"],
            "region":  row["region"],
            "words":   {},
            "phrases": {},
        }

    for row in conn.execute(
        "SELECT dialect_key, literary, dialect_form, category, pos FROM words"
    ):
        dk  = row["dialect_key"]
        cat = row["category"]
        if dk in data["dialects"]:
            data["dialects"][dk][cat][row["literary"]] = row["dialect_form"]
        if row["pos"]:
            data["word_pos"][row["literary"]] = row["pos"]

    conn.close()
    return data


# ══════════════════════════════════════════════════════════════════════════════
# Таҳлил — SQL-асос (як query барои тамоми матн)
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# Морфологияи тоҷикӣ — пешванд / реша / пасванд
# ══════════════════════════════════════════════════════════════════════════════

_SUFFIXES = [
    # Ҷамъ + ҳолат (аз дарозтарин то кӯтоҳтарин)
    "ҳоямон", "ҳоятон", "ҳоашон",
    "ҳоро", "онро", "ёнро",
    "ҳои", "ҳо", "ёни", "ён", "они", "он",
    # Пасванди соҳибӣ + ҳолат
    "амонро", "атонро", "ашонро",
    "амон", "атон", "ашон",
    "амро", "атро", "ашро",
    "аш", "ат", "ам",
    # Ҳолат
    "ро",
    # Пасвандҳои сифатӣ/исмӣ
    "она", "нок", "вор", "манд", "зор", "гар", "кор", "бон", "дор",
    # Феъли шахсӣ + шахси 1 баъди садонок (-ям = й+ам)
    "анд", "ям", "ем", "ед", "ад",
    # Ёидовар / мавсуфӣ
    "ӣ", "е", "и",
    # Пайвандки "-у" (ва)
    "у",
]

_PREFIXES = [
    "намеха", "намехо", "наме",
    "мехо", "меха", "ме",
    "на", "бе", "ба", "ҳам",
]

# Пасвандҳои -ям → адабӣ "-ам" (баъди садонок)
_VOWELS = set("аеёиоуэюяӣӯ")

_MIN_STEM = 2


def morph_stems(word: str) -> list[str]:
    """Вариантҳои морфологии ресаи калимаро бармегардонад."""
    wl = word.strip().lower()
    stems: list[str] = []

    base = wl
    for pref in _PREFIXES:
        if wl.startswith(pref) and len(wl) > len(pref) + _MIN_STEM:
            base = wl[len(pref):]
            break

    for cand in ([base, wl] if base != wl else [wl]):
        for suf in _SUFFIXES:
            if cand.endswith(suf) and len(cand) > len(suf) + _MIN_STEM:
                root = cand[:-len(suf)]
                if root not in stems:
                    stems.append(root)
                inf = root + "идан"
                if inf not in stems:
                    stems.append(inf)

    return stems


def correct_elision(word: str) -> str | None:
    """
    Садоноки «а»-и партофташударо барқарор мекунад.
    Мисол: бародарм → бародарам  (лаҳҷавӣ)
           китобш   → китобаш
           дӯстт    → дӯстат
    Бармегардонад: шакли ислоҳшуда ё None.
    """
    wl = word.strip().lower()
    if len(wl) < 3:
        return None
    if wl[-2] in _VOWELS:
        return None   # садонок аллакай мавҷуд аст — ислоҳ лозим нест
    corrections = {"м": "ам", "т": "ат", "ш": "аш", "д": "ад"}
    repl = corrections.get(wl[-1])
    if repl:
        return wl[:-1] + repl
    return None


def morph_classify(unknown_tokens: list[str]) -> dict[str, tuple]:
    """
    Барои калимаҳои нешинохташуда таҳлили морфологӣ мекунад.
    Бармегардонад: {token_lower: (dialect_keys, literary_form, word_type)}
      word_type: "dialect_stem" | "literary_stem"
    """
    if not unknown_tokens:
        return {}

    tok_stems: dict[str, list[str]] = {}
    for tok in unknown_tokens:
        stems = morph_stems(tok.lower())
        if stems:
            tok_stems[tok.lower()] = stems

    if not tok_stems:
        return {}

    all_stems = list({s for lst in tok_stems.values() for s in lst})
    ph = ",".join("?" * len(all_stems))

    conn = get_connection()
    rows = conn.execute(f"""
        SELECT dialect_key,
               lower(literary)     AS lit,
               lower(dialect_form) AS form,
               literary            AS lit_orig
        FROM words
        WHERE lower(literary)     IN ({ph})
           OR lower(dialect_form) IN ({ph})
    """, all_stems + all_stems).fetchall()
    conn.close()

    stem_set = set(all_stems)
    # stem → {form_dks, lit_dks, lit_form}
    stem_info: dict[str, dict] = {}
    for row in rows:
        dk, lit, form, lit_orig = row["dialect_key"], row["lit"], row["form"], row["lit_orig"]
        if form in stem_set and form != lit:
            d = stem_info.setdefault(form, {"form_dks": [], "lit_dks": [], "lit_form": lit_orig})
            if dk not in d["form_dks"]:
                d["form_dks"].append(dk)
        if lit in stem_set:
            d = stem_info.setdefault(lit, {"form_dks": [], "lit_dks": [], "lit_form": lit_orig})
            if dk not in d["lit_dks"]:
                d["lit_dks"].append(dk)

    results: dict[str, tuple] = {}
    for tl, stems in tok_stems.items():
        for stem in stems:
            if stem not in stem_info:
                continue
            si = stem_info[stem]
            if si["form_dks"]:
                results[tl] = (si["form_dks"], si["lit_form"], "dialect_stem")
                break
            if si["lit_dks"]:
                results[tl] = (si["lit_dks"], stem, "literary_stem")
                break

    return results


def classify_word(word: str) -> dict:
    """
    Муайян мекунад ки оё калима адабист ё лаҳҷавӣ.

    Баргардонад:
      is_literary_only — танҳо дар сутуни literary ёфт шуд (шакли стандартӣ)
      is_dialect_form  — дар сутуни dialect_form ёфт шуд (шакли лаҳҷавӣ)
      literary_form    — шакли адабии он (агар dialect_form бошад, literary-аш)
      dialect_keys     — калидҳои лаҳҷаҳое ки ин калима дар онҳост
    """
    wl = word.strip().lower()
    conn = get_connection()
    rows = conn.execute("""
        SELECT dialect_key, lower(literary) AS lit, lower(dialect_form) AS form
        FROM words
        WHERE lower(literary) = ? OR lower(dialect_form) = ?
    """, (wl, wl)).fetchall()
    conn.close()

    as_literary = [r for r in rows if r["lit"] == wl]
    as_dialect  = [r for r in rows if r["form"] == wl]

    lit_form = as_dialect[0]["lit"] if as_dialect else wl
    dk_list  = list({r["dialect_key"] for r in as_dialect}) or \
               list({r["dialect_key"] for r in as_literary})

    return {
        "word":             word,
        "is_literary_only": bool(as_literary) and not as_dialect,
        "is_dialect_form":  bool(as_dialect),
        "literary_form":    lit_form,
        "dialect_keys":     dk_list,
    }


def detect_dialect(tokens: list[str]) -> tuple[dict, list]:
    """
    Лаҳҷаро аз рӯи феҳристи токенҳо муайян мекунад.

    Баргардонад: (scores_dict, word_results_list)
    word_results → [(tok, matched_dialects, word_type), ...]
      word_type: "dialect"  — лаҳҷавӣ (dialect_form дар база)
                 "literary" — адабӣ (танҳо literary дар база)
                 "both"     — ҳарду сутун дошт
                 "unknown"  — дар база нест
    """
    if not tokens:
        return {}, []

    tl_list = list({t.lower() for t in tokens})
    tl_set  = set(tl_list)
    ph      = ",".join("?" * len(tl_list))

    conn = get_connection()

    rows = conn.execute(f"""
        SELECT dialect_key,
               lower(literary)     AS lit,
               lower(dialect_form) AS form
        FROM words
        WHERE lower(literary)     IN ({ph})
           OR lower(dialect_form) IN ({ph})
    """, tl_list + tl_list).fetchall()

    all_dialects = [r["key"] for r in conn.execute(
        "SELECT key FROM dialects ORDER BY sort_order, rowid")]
    conn.close()

    scores = {dk: 0 for dk in all_dialects}

    # Ду харита: form_map — калимаи лаҳҷавӣ, lit_map — калимаи адабӣ
    form_map: dict[str, list] = {}   # token_lower → [dk] (dialect_form match)
    lit_map:  dict[str, list] = {}   # token_lower → [dk] (literary match only)

    for row in rows:
        dk, lit, form = row["dialect_key"], row["lit"], row["form"]
        if form in tl_set and form != lit:
            lst = form_map.setdefault(form, [])
            if dk not in lst:
                lst.append(dk)
        if lit in tl_set:
            lst = lit_map.setdefault(lit, [])
            if dk not in lst:
                lst.append(dk)

    word_results = []
    for tok in tokens:
        tl = tok.lower()
        form_dks = form_map.get(tl, [])
        lit_dks  = lit_map.get(tl, [])

        if form_dks:
            # Лаҳҷавӣ — ба ҳисоб меравад
            for dk in form_dks:
                scores[dk] += 1
            wtype = "both" if lit_dks else "dialect"
            word_results.append((tok, form_dks, wtype))
        elif lit_dks:
            # Танҳо адабӣ — ба ҳисоб намеравад (шакли стандартӣ)
            word_results.append((tok, lit_dks, "literary"))
        else:
            word_results.append((tok, [], "unknown"))

    return scores, word_results


# ══════════════════════════════════════════════════════════════════════════════
# Ёрдамчиҳо
# ══════════════════════════════════════════════════════════════════════════════

def find_literary(word: str, dialect_keys: list[str] | None = None) -> str:
    """Адабии калимаи лаҳҷавиро меёбад."""
    wl = word.lower()
    conn = get_connection()
    if dialect_keys:
        ph  = ",".join("?" * len(dialect_keys))
        row = conn.execute(f"""
            SELECT literary FROM words
            WHERE lower(dialect_form) = ? AND dialect_key IN ({ph})
            LIMIT 1
        """, [wl] + dialect_keys).fetchone()
    else:
        row = conn.execute("""
            SELECT literary FROM words
            WHERE lower(dialect_form) = ?
            LIMIT 1
        """, (wl,)).fetchone()
    conn.close()
    return row["literary"] if row else word


def find_variants(literary_word: str) -> dict[str, str]:
    """Ҳамаи вариантҳои лаҳҷавии калимаи адабиро меёбад: {dk: dialect_form}."""
    wl = literary_word.lower()
    conn = get_connection()
    rows = conn.execute("""
        SELECT w.dialect_key, w.dialect_form
        FROM words w
        JOIN dialects d ON d.key = w.dialect_key
        WHERE lower(w.literary) = ? AND w.category = 'words'
        ORDER BY d.sort_order, d.rowid
    """, (wl,)).fetchall()
    conn.close()
    return {r["dialect_key"]: r["dialect_form"] for r in rows}


def get_pos(literary_word: str) -> str:
    """Ҷузъи нутқи калимаро аз база меёбад."""
    wl = literary_word.lower()
    conn = get_connection()
    row = conn.execute("""
        SELECT pos FROM words
        WHERE lower(literary) = ? AND pos != ''
        LIMIT 1
    """, (wl,)).fetchone()
    conn.close()
    return row["pos"] if row else ""


# ══════════════════════════════════════════════════════════════════════════════
# Навиштан
# ══════════════════════════════════════════════════════════════════════════════

def add_word(dialect_key: str, literary: str, dialect_form: str,
             category: str = "words", pos: str = "") -> str:
    """
    Калима ё ҷумларо илова мекунад ё навсозӣ.
    Бармегардонад: "added" | "updated" | "unchanged" | "skipped"
    """
    lit = literary.strip().lower()
    df  = dialect_form.strip()
    if not lit or not df:
        return "skipped"

    conn = get_connection()

    # Ҳамон ҷуфти дақиқ мавҷуд аст?
    exact = conn.execute("""
        SELECT id FROM words
        WHERE dialect_key = ? AND lower(literary) = ?
          AND lower(dialect_form) = ? AND category = ?
    """, (dialect_key, lit, df.lower(), category)).fetchone()

    if exact:
        if pos:
            conn.execute("UPDATE words SET pos = ? WHERE id = ?", (pos, exact["id"]))
            conn.commit()
        conn.close()
        return "unchanged"

    # Адабии ҳамон лаҳҷа мавҷуд, вале шакли лаҳҷавӣ фарқ мекунад
    lit_row = conn.execute("""
        SELECT id FROM words
        WHERE dialect_key = ? AND lower(literary) = ? AND category = ?
    """, (dialect_key, lit, category)).fetchone()

    if lit_row:
        conn.execute("UPDATE words SET dialect_form = ?, pos = ? WHERE id = ?",
                     (df, pos, lit_row["id"]))
        conn.commit()
        conn.close()
        return "updated"

    conn.execute("""
        INSERT INTO words (dialect_key, literary, dialect_form, category, pos)
        VALUES (?, ?, ?, ?, ?)
    """, (dialect_key, lit, df, category, pos))
    conn.commit()
    conn.close()
    return "added"


def add_dialect(key: str, name: str, region: str = "",
                sort_order: int = 0) -> bool:
    """Лаҳҷаи нав илова мекунад."""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO dialects (key, name, region, sort_order)
            VALUES (?, ?, ?, ?)
        """, (key, name, region, sort_order))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def update_dialect(key: str, name: str, region: str, sort_order: int) -> bool:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE dialects SET name=?, region=?, sort_order=? WHERE key=?",
            (name, region, sort_order, key))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def delete_dialect(key: str) -> bool:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM dialects WHERE key=?", (key,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def delete_word(word_id: int) -> bool:
    conn = get_connection()
    conn.execute("DELETE FROM words WHERE id = ?", (word_id,))
    conn.commit()
    conn.close()
    return True


def stats() -> dict:
    """Омори умумӣ."""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
    rows  = conn.execute("""
        SELECT d.name, COUNT(w.id) as cnt
        FROM dialects d
        LEFT JOIN words w ON w.dialect_key = d.key
        GROUP BY d.key
        ORDER BY cnt DESC
    """).fetchall()
    conn.close()
    return {"total": total, "per_dialect": [dict(r) for r in rows]}


# ══════════════════════════════════════════════════════════════════════════════
# Тарҷума (translator)
# ══════════════════════════════════════════════════════════════════════════════

def translate_phrase(text: str, dialect_key: str) -> str:
    norm = text.strip().lower()
    conn = get_connection()

    # 1. Пурра ҷумла
    row = conn.execute("""
        SELECT dialect_form FROM words
        WHERE dialect_key = ? AND lower(literary) = ? AND category = 'phrases'
        LIMIT 1
    """, (dialect_key, norm)).fetchone()
    if row:
        conn.close()
        return row["dialect_form"]

    # 2. Калима ба калима
    words_rows = conn.execute("""
        SELECT lower(literary) as lit, dialect_form FROM words
        WHERE dialect_key = ? AND category = 'words'
    """, (dialect_key,)).fetchall()
    conn.close()

    words_map = {r["lit"]: r["dialect_form"] for r in words_rows}
    tokens = re.findall(r"[\wЀ-ӿ]+|[^\wЀ-ӿ]", text, re.UNICODE)
    result = []
    for token in tokens:
        lower = token.lower()
        if lower in words_map:
            translated = words_map[lower]
            if token[0].isupper():
                translated = translated.capitalize()
            result.append(translated)
        else:
            result.append(token)
    return "".join(result)


# ══════════════════════════════════════════════════════════════════════════════
# Вилоятҳо (Provinces)
# ══════════════════════════════════════════════════════════════════════════════

def get_provinces() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT key, name, sort_order FROM provinces ORDER BY sort_order"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_province(key: str, name: str, sort_order: int = 0) -> bool:
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO provinces (key, name, sort_order) VALUES (?,?,?)",
        (key, name, sort_order)
    )
    conn.commit()
    conn.close()
    return True


def get_dialects_by_province() -> dict[str, list[dict]]:
    """Ноҳияҳоро аз рӯи вилоят ҷудо мекунад."""
    conn = get_connection()
    dialects = conn.execute(
        "SELECT key, name, region, province_key, sort_order "
        "FROM dialects ORDER BY sort_order, rowid"
    ).fetchall()
    conn.close()
    result: dict[str, list[dict]] = {}
    for d in dialects:
        pk = d["province_key"] or "other"
        result.setdefault(pk, []).append(dict(d))
    return result


def link_to_province(dialect_key: str, province_key: str) -> bool:
    conn = get_connection()
    conn.execute(
        "UPDATE dialects SET province_key = ? WHERE key = ?",
        (province_key, dialect_key)
    )
    conn.commit()
    conn.close()
    return True


# ══════════════════════════════════════════════════════════════════════════════
# Решаҳо (Roots)
# ══════════════════════════════════════════════════════════════════════════════

def get_roots(pos: str = "") -> list[dict]:
    conn = get_connection()
    if pos:
        rows = conn.execute(
            "SELECT * FROM roots WHERE pos = ? ORDER BY root", (pos,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM roots ORDER BY root").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_root(root: str, pos: str = "", meaning: str = "", notes: str = "") -> str:
    """Бармегардонад: 'added' | 'updated' | 'skipped'"""
    r = root.strip().lower()
    if not r:
        return "skipped"
    conn = get_connection()
    existing = conn.execute("SELECT id FROM roots WHERE root = ?", (r,)).fetchone()
    if existing:
        conn.execute(
            "UPDATE roots SET pos=?, meaning=?, notes=? WHERE id=?",
            (pos, meaning, notes, existing["id"])
        )
        conn.commit()
        conn.close()
        return "updated"
    conn.execute(
        "INSERT INTO roots (root, pos, meaning, notes) VALUES (?,?,?,?)",
        (r, pos, meaning, notes)
    )
    conn.commit()
    conn.close()
    return "added"


def get_root(word: str) -> dict | None:
    """Решаи калимаро меёбад (дақиқ ё морфологӣ)."""
    wl = word.strip().lower()
    conn = get_connection()
    row = conn.execute("SELECT * FROM roots WHERE lower(root) = ?", (wl,)).fetchone()
    conn.close()
    return dict(row) if row else None


def link_word_to_root(literary: str, root_word: str) -> bool:
    """Калимаи адабиро ба реша пайваст мекунад."""
    conn = get_connection()
    root_row = conn.execute(
        "SELECT id FROM roots WHERE lower(root) = ?", (root_word.lower(),)
    ).fetchone()
    if not root_row:
        conn.close()
        return False
    conn.execute(
        "UPDATE words SET root_id = ? WHERE lower(literary) = ?",
        (root_row["id"], literary.lower())
    )
    conn.commit()
    conn.close()
    return True


# ══════════════════════════════════════════════════════════════════════════════
# Пешвандҳо (Prefixes)
# ══════════════════════════════════════════════════════════════════════════════

def get_prefixes(category: str = "") -> list[dict]:
    conn = get_connection()
    if category:
        rows = conn.execute(
            "SELECT * FROM prefixes WHERE category=? ORDER BY prefix", (category,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM prefixes ORDER BY prefix").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_prefix(prefix: str, meaning: str = "", category: str = "") -> str:
    """Бармегардонад: 'added' | 'updated' | 'skipped'"""
    p = prefix.strip()
    if not p:
        return "skipped"
    conn = get_connection()
    ex = conn.execute("SELECT id FROM prefixes WHERE prefix=?", (p,)).fetchone()
    if ex:
        conn.execute(
            "UPDATE prefixes SET meaning=?, category=? WHERE id=?",
            (meaning, category, ex["id"])
        )
        conn.commit()
        conn.close()
        return "updated"
    conn.execute(
        "INSERT INTO prefixes (prefix, meaning, category) VALUES (?,?,?)",
        (p, meaning, category)
    )
    conn.commit()
    conn.close()
    return "added"


# ══════════════════════════════════════════════════════════════════════════════
# Пасвандҳо (Suffixes)
# ══════════════════════════════════════════════════════════════════════════════

def get_suffixes(category: str = "") -> list[dict]:
    conn = get_connection()
    if category:
        rows = conn.execute(
            "SELECT * FROM suffixes WHERE category=? ORDER BY suffix", (category,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM suffixes ORDER BY suffix").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_suffix(suffix: str, meaning: str = "", category: str = "",
               pos_from: str = "", pos_to: str = "") -> str:
    """Бармегардонад: 'added' | 'updated' | 'skipped'"""
    s = suffix.strip()
    if not s:
        return "skipped"
    conn = get_connection()
    ex = conn.execute("SELECT id FROM suffixes WHERE suffix=?", (s,)).fetchone()
    if ex:
        conn.execute(
            "UPDATE suffixes SET meaning=?, category=?, pos_from=?, pos_to=? WHERE id=?",
            (meaning, category, pos_from, pos_to, ex["id"])
        )
        conn.commit()
        conn.close()
        return "updated"
    conn.execute(
        "INSERT INTO suffixes (suffix, meaning, category, pos_from, pos_to) VALUES (?,?,?,?,?)",
        (s, meaning, category, pos_from, pos_to)
    )
    conn.commit()
    conn.close()
    return "added"


# ══════════════════════════════════════════════════════════════════════════════
# Шаклҳои феъл (Verb forms)
# ══════════════════════════════════════════════════════════════════════════════

def get_verb_forms(root: str = "") -> list[dict]:
    conn = get_connection()
    if root:
        rows = conn.execute("""
            SELECT vf.*, r.root, r.meaning
            FROM verb_forms vf
            LEFT JOIN roots r ON r.id = vf.root_id
            WHERE lower(r.root) = ?
            ORDER BY vf.infinitive
        """, (root.lower(),)).fetchall()
    else:
        rows = conn.execute("""
            SELECT vf.*, r.root, r.meaning
            FROM verb_forms vf
            LEFT JOIN roots r ON r.id = vf.root_id
            ORDER BY vf.infinitive
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_verb_form(infinitive: str, present_stem: str = "", past_stem: str = "",
                  verb_class: str = "", root_word: str = "") -> str:
    """Шакли феълро ба база илова мекунад."""
    inf = infinitive.strip().lower()
    if not inf:
        return "skipped"
    conn = get_connection()

    root_id = None
    if root_word:
        rrow = conn.execute(
            "SELECT id FROM roots WHERE lower(root) = ?", (root_word.lower(),)
        ).fetchone()
        if rrow:
            root_id = rrow["id"]

    ex = conn.execute(
        "SELECT id FROM verb_forms WHERE lower(infinitive) = ?", (inf,)
    ).fetchone()

    if ex:
        conn.execute(
            "UPDATE verb_forms SET present_stem=?, past_stem=?, verb_class=?, root_id=? WHERE id=?",
            (present_stem, past_stem, verb_class, root_id, ex["id"])
        )
        conn.commit()
        conn.close()
        return "updated"

    conn.execute(
        "INSERT INTO verb_forms (root_id, infinitive, present_stem, past_stem, verb_class)"
        " VALUES (?,?,?,?,?)",
        (root_id, inf, present_stem, past_stem, verb_class)
    )
    conn.commit()
    conn.close()
    return "added"


# ══════════════════════════════════════════════════════════════════════════════
# Калимаҳои сермаъно (Polysemy)
# ══════════════════════════════════════════════════════════════════════════════

def get_polysemy(word: str = "") -> list[dict]:
    """Ҳамаи маъноҳои калимаро мегирад; бе аргумент ҳамаи ҷадвалро мебарад."""
    conn = get_connection()
    if word.strip():
        rows = conn.execute(
            "SELECT * FROM polysemy WHERE lower(word) = ? ORDER BY word, meaning_num",
            (word.strip().lower(),)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM polysemy ORDER BY word, meaning_num"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_polysemy(word: str, meaning_num: int = 0, pos: str = "",
                 meaning: str = "", example: str = "", domain: str = "") -> str:
    """Маъноро ба калима илова мекунад. meaning_num=0 → автоматӣ."""
    wl = word.strip().lower()
    if not wl or not meaning.strip():
        return "skipped"
    conn = get_connection()
    if meaning_num <= 0:
        last = conn.execute(
            "SELECT MAX(meaning_num) as mx FROM polysemy WHERE lower(word) = ?", (wl,)
        ).fetchone()
        meaning_num = (last["mx"] or 0) + 1

    dup = conn.execute(
        "SELECT id FROM polysemy WHERE lower(word)=? AND meaning_num=?",
        (wl, meaning_num)
    ).fetchone()
    if dup:
        conn.close()
        return "exists"

    conn.execute(
        "INSERT INTO polysemy (word, meaning_num, pos, meaning, example, domain)"
        " VALUES (?,?,?,?,?,?)",
        (wl, meaning_num, pos, meaning.strip(), example, domain)
    )
    conn.commit()
    conn.close()
    return "added"


def update_polysemy(poly_id: int, word: str, meaning_num: int, pos: str,
                    meaning: str, example: str, domain: str):
    conn = get_connection()
    conn.execute(
        "UPDATE polysemy SET word=?, meaning_num=?, pos=?, meaning=?, example=?, domain=?"
        " WHERE id=?",
        (word.strip().lower(), meaning_num, pos, meaning.strip(), example, domain, poly_id)
    )
    conn.commit()
    conn.close()


def delete_polysemy(poly_id: int) -> bool:
    conn = get_connection()
    conn.execute("DELETE FROM polysemy WHERE id=?", (poly_id,))
    conn.commit()
    conn.close()
    return True


def search_polysemy(query: str) -> list[dict]:
    """Ҷустуҷӯ дар калимаҳои сермаъно."""
    q = f"%{query.lower()}%"
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM polysemy WHERE lower(word) LIKE ? OR lower(meaning) LIKE ?"
        " ORDER BY word, meaning_num",
        (q, q)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# Таҳлили морфологии пурра — реша + пешванд + пасванд + лаҳҷавӣ/адабӣ
# ══════════════════════════════════════════════════════════════════════════════

def morph_analyze_word(word: str) -> dict:
    """
    Калимаро ба морфемаҳо тақсим мекунад ва ҳар қисмро
    ҳамчун адабӣ ё лаҳҷавӣ муайян мекунад.

    Бармегардонад:
    {
      "original":   str,
      "prefix":     {"form": str, "is_dialectal": bool, "literary": str, "meaning": str},
      "root":       {"form": str, "is_dialectal": bool, "literary": str,
                     "dialect_keys": list, "found": bool},
      "suffix":     {"form": str, "is_dialectal": bool, "literary": str,
                     "meaning": str, "dialect_keys": list},
      "literary_reconstruction": str,
      "summary":    str,   # тавсифи мухтасар
    }
    """
    wl = word.strip().lower()
    conn = get_connection()

    # ── 1. Пешванд ─────────────────────────────────────────────────────────
    found_prefix = ""
    prefix_is_dial = False
    prefix_literary = ""
    after_prefix = wl
    for pref in _PREFIXES:
        if wl.startswith(pref) and len(wl) > len(pref) + _MIN_STEM:
            found_prefix = pref
            after_prefix = wl[len(pref):]
            break

    # ── 2. Пасванд — аввал аз ҷадвали suffixes (бо is_dialectal) ──────────
    found_suffix = ""
    suffix_is_dial = False
    suffix_literary = ""
    suffix_meaning  = ""
    suffix_dk_list  = []
    best_root_cand  = after_prefix

    # Пешсанҷ: -ям баъди садонок (шахси 1 ҳозира: гӯ+ям, о+ям)
    # Бояд пеш аз DB-loop бошад, зеро "-м" (1 ҳарф) зудтар мегирад
    if (not found_suffix
            and after_prefix.endswith("ям")
            and len(after_prefix) >= 2 + _MIN_STEM
            and after_prefix[-3] in _VOWELS):
        found_suffix    = "ям"
        suffix_is_dial  = False
        suffix_literary = "ям"
        best_root_cand  = after_prefix[:-2]

    # Тартиб: аз дарозтарин то кӯтоҳтарин
    db_suffixes = conn.execute(
        "SELECT suffix, is_dialectal, literary_suffix, meaning, dialect_keys"
        " FROM suffixes ORDER BY length(suffix) DESC"
    ).fetchall()

    for row in db_suffixes:
        if found_suffix:   # аллакай дар пешсанҷ ёфт шуд
            break
        # Suffixes in DB may be stored as "-ам" or "ам"; normalise by stripping leading dash
        s_raw = row["suffix"]
        s = s_raw.lstrip("-")
        if not s:
            continue
        if after_prefix.endswith(s) and len(after_prefix) > len(s) + _MIN_STEM:
            found_suffix    = s
            suffix_is_dial  = bool(row["is_dialectal"])
            lit_raw         = row["literary_suffix"] or s_raw
            suffix_literary = lit_raw.lstrip("-") if lit_raw else s
            suffix_meaning  = row["meaning"] or ""
            suffix_dk_list  = [k.strip() for k in (row["dialect_keys"] or "").split(",") if k.strip()]
            best_root_cand  = after_prefix[:-len(s)]
            break

    # Агар дар ҷадвал нашуд — аз рӯйхати дохилӣ (_SUFFIXES) санҷ
    if not found_suffix:
        for suf in _SUFFIXES:
            if after_prefix.endswith(suf) and len(after_prefix) > len(suf) + _MIN_STEM:
                found_suffix    = suf
                # -ям баъди садонок = -ам адабӣ
                if suf == "ям" and len(after_prefix) >= 3 and after_prefix[-3] in _VOWELS:
                    suffix_literary = "ам"
                elif suf == "у":
                    suffix_literary = ""   # пайвандак, дар адабӣ ҷудо нест
                else:
                    suffix_literary = suf
                best_root_cand = after_prefix[:-len(suf)]
                break

    # ── 3. Реша ────────────────────────────────────────────────────────────
    root_cands = [best_root_cand]
    if found_prefix:
        root_cands.append(found_prefix + best_root_cand)
        root_cands.append(wl)

    root_found    = False
    root_is_dial  = False
    root_literary = best_root_cand
    root_dk_list  = []
    _matched_cand = None

    # Пешвандҳои феълӣ: verb_forms аввал санҷида мешавад
    # (то калимаи ғайрифеъл дар words хато нагирад, мисл: кун=рӯз дар Исфара)
    _VERBAL_PREFIXES = {"ме", "меха", "мехо", "наме", "намеха", "намехо", "на"}
    if found_prefix in _VERBAL_PREFIXES:
        for cand in [best_root_cand, found_prefix + best_root_cand]:
            r = conn.execute(
                """SELECT present_stem FROM verb_forms
                   WHERE lower(present_stem)=? OR lower(past_stem)=?""",
                (cand, cand)
            ).fetchone()
            if r:
                root_found    = True
                root_is_dial  = False
                root_literary = cand
                _matched_cand = cand
                break

    # Words (literary ё dialect_form)
    if not root_found:
        for cand in root_cands:
            r = conn.execute(
                "SELECT DISTINCT literary FROM words WHERE lower(literary)=?", (cand,)
            ).fetchone()
            if r:
                root_found    = True
                root_is_dial  = False
                root_literary = r["literary"]
                _matched_cand = cand
                break
            rows = conn.execute(
                "SELECT literary, dialect_key FROM words WHERE lower(dialect_form)=?", (cand,)
            ).fetchall()
            if rows:
                root_found    = True
                root_is_dial  = True
                root_literary = rows[0]["literary"]
                root_dk_list  = [rr["dialect_key"] for rr in rows]
                _matched_cand = cand
                break

    # Roots ҷадвал
    if not root_found:
        for cand in [best_root_cand, found_prefix + best_root_cand]:
            r = conn.execute(
                "SELECT root FROM roots WHERE lower(root)=?", (cand,)
            ).fetchone()
            if r:
                root_found    = True
                root_is_dial  = False
                root_literary = r["root"]
                _matched_cand = cand
                break

    # Verb_forms (барои пешвандҳои ғайрифеълӣ ё агар дар боло нашуд)
    if not root_found:
        for cand in [best_root_cand, found_prefix + best_root_cand]:
            r = conn.execute(
                """SELECT present_stem FROM verb_forms
                   WHERE lower(present_stem)=? OR lower(past_stem)=?""",
                (cand, cand)
            ).fetchone()
            if r:
                root_found    = True
                root_is_dial  = False
                root_literary = cand
                _matched_cand = cand
                break

    conn.close()

    # ── 4. Барқарорсозии шакли адабӣ ───────────────────────────────────────
    # Агар "-у" пайвандак бошад — дар барқарорсозӣ нест мешавад
    if found_suffix == "у" and not suffix_is_dial:
        found_suffix = ""
        suffix_literary = ""
    lit_suf  = suffix_literary if suffix_literary else found_suffix
    lit_suf  = lit_suf.lstrip("-") if lit_suf.startswith("-") else lit_suf

    _pref_in_root = (_matched_cand is not None and _matched_cand != best_root_cand
                     and _matched_cand != wl)

    def _safe_join(base: str, suf: str) -> str:
        """Агар base аллакай ба suf тамом шавад — дубора намегузорад."""
        if suf and base.endswith(suf):
            return base
        return base + suf

    if _matched_cand == wl:
        # Калимаи пурра (бо пасванд) ёфт шуд — literary = худи калима
        literary     = root_literary if root_found else wl
        found_prefix = ""
        found_suffix = ""
    elif _pref_in_root:
        # Пешванд + реша ёфт шуд (масалан "бародар") — пасванд ҷудо, пешванд дар реша
        base     = root_literary if root_found else best_root_cand
        literary = _safe_join(base, lit_suf)
        found_prefix = ""
    else:
        lit_root = root_literary if root_found else best_root_cand
        literary = found_prefix + _safe_join(lit_root, lit_suf)

    # ── 5. Тавсиф ──────────────────────────────────────────────────────────
    parts = []
    if found_prefix:
        parts.append(f"пешванд «{found_prefix}»: адабӣ")
    if root_found:
        status = "лаҳҷавӣ" if root_is_dial else "адабӣ"
        parts.append(f"реша «{best_root_cand}»: {status}")
        if root_is_dial:
            parts.append(f"  (адабии реша: «{root_literary}»)")
    else:
        parts.append(f"реша «{best_root_cand}»: дар база нест")
    if found_suffix:
        status = "лаҳҷавӣ" if suffix_is_dial else "адабӣ"
        parts.append(f"пасванд «{found_suffix}»: {status}")
        if suffix_is_dial and suffix_literary and suffix_literary != found_suffix:
            parts.append(f"  (адабии пасванд: «{suffix_literary}»)")

    summary = " | ".join(parts)
    if literary.lower() != wl:
        summary += f" → адабӣ: «{literary}»"

    return {
        "original": word,
        "prefix": {
            "form": found_prefix,
            "is_dialectal": prefix_is_dial,
            "literary": prefix_literary or found_prefix,
            "meaning": "",
        },
        "root": {
            "form": best_root_cand,
            "is_dialectal": root_is_dial,
            "literary": root_literary,
            "dialect_keys": root_dk_list,
            "found": root_found,
        },
        "suffix": {
            "form": found_suffix,
            "is_dialectal": suffix_is_dial,
            "literary": suffix_literary,
            "meaning": suffix_meaning,
            "dialect_keys": suffix_dk_list,
        },
        "literary_reconstruction": literary,
        "summary": summary,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Тарҷумаи ҷумлаи лаҳҷавӣ ба адабӣ
# ══════════════════════════════════════════════════════════════════════════════

def phrase_to_literary(text: str) -> dict:
    """
    Матни лаҳҷавиро ба адабӣ мегардонад.

    Бармегардонад:
    {
      "original":  str,
      "literary":  str,           # тарҷумаи адабӣ
      "tokens":    list[dict],    # ҳар калима ва тарҷумааш
      "lit_words": list[str],     # калимаҳое ки дар базаи адабӣ ёфт шуданд
      "changed":   int,           # шумораи калимаҳои тағйирёфта
    }
    """
    import re
    # Ҷудо кардани токенҳо (калима + аломатҳои пунктуатсия)
    tokens_raw = re.findall(r"[\wЀ-ӿ؀-ۿ]+|[^\wЀ-ӿ؀-ۿ]+",
                            text)

    conn = get_connection()
    result_tokens = []
    lit_words = []
    changed = 0

    for tok in tokens_raw:
        # Аломатҳои ғайрикалимавӣ — бетағйир
        if not re.search(r"[Ѐ-ӿ؀-ۿa-zA-Z]", tok):
            result_tokens.append({"original": tok, "literary": tok, "changed": False})
            continue

        wl = tok.strip().lower()

        # 1. Ҷустуҷӯ дар ҷадвали words ҳамчун dialect_form
        rows = conn.execute(
            "SELECT literary FROM words WHERE lower(dialect_form)=? LIMIT 1", (wl,)
        ).fetchall()
        if rows:
            lit = rows[0]["literary"]
            # Нигоҳ доштани ҳарфи калони аввал
            if tok[0].isupper():
                lit = lit[0].upper() + lit[1:]
            result_tokens.append({"original": tok, "literary": lit, "changed": lit.lower() != wl})
            if lit.lower() != wl:
                lit_words.append(lit)
                changed += 1
            continue

        # 2. Таҳлили морфологӣ
        conn.close()
        morph = morph_analyze_word(tok)
        conn = get_connection()

        lit = morph["literary_reconstruction"]
        is_changed = lit.lower() != wl and morph["root"]["found"]

        if tok[0].isupper() and lit:
            lit = lit[0].upper() + lit[1:]

        result_tokens.append({"original": tok, "literary": lit if is_changed else tok,
                               "changed": is_changed})
        if is_changed:
            lit_words.append(lit)
            changed += 1

    conn.close()

    literary_parts = [t["literary"] for t in result_tokens]
    literary = "".join(literary_parts)

    return {
        "original":  text,
        "literary":  literary,
        "tokens":    result_tokens,
        "lit_words": lit_words,
        "changed":   changed,
    }


# ══════════════════════════════════════════════════════════════════════════════
# CRUD-ёрдамчиҳо барои manage_linguistic.py
# ══════════════════════════════════════════════════════════════════════════════

# ── Решаҳо ───────────────────────────────────────────────────────────────────

def get_root_by_id(root_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM roots WHERE id = ?", (root_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_root_by_name(name: str) -> dict | None:
    wl = name.strip().lower()
    conn = get_connection()
    row = conn.execute("SELECT * FROM roots WHERE lower(root) = ?", (wl,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_root(root_id: int, root: str, pos: str, meaning: str, notes: str):
    conn = get_connection()
    conn.execute(
        "UPDATE roots SET root=?, pos=?, meaning=?, notes=? WHERE id=?",
        (root.strip().lower(), pos, meaning, notes, root_id)
    )
    conn.commit()
    conn.close()


def delete_root(root_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM roots WHERE id=?", (root_id,))
    conn.commit()
    conn.close()


# ── Пешвандҳо ────────────────────────────────────────────────────────────────

def update_prefix(prefix_id: int, prefix: str, meaning: str, category: str):
    conn = get_connection()
    conn.execute(
        "UPDATE prefixes SET prefix=?, meaning=?, category=? WHERE id=?",
        (prefix.strip(), meaning, category, prefix_id)
    )
    conn.commit()
    conn.close()


def delete_prefix(prefix_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM prefixes WHERE id=?", (prefix_id,))
    conn.commit()
    conn.close()


# ── Пасвандҳо ────────────────────────────────────────────────────────────────

def update_suffix(suffix_id: int, suffix: str, meaning: str, category: str,
                  pos_from: str, pos_to: str):
    conn = get_connection()
    conn.execute(
        "UPDATE suffixes SET suffix=?, meaning=?, category=?, pos_from=?, pos_to=?"
        " WHERE id=?",
        (suffix.strip(), meaning, category, pos_from, pos_to, suffix_id)
    )
    conn.commit()
    conn.close()


def delete_suffix(suffix_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM suffixes WHERE id=?", (suffix_id,))
    conn.commit()
    conn.close()


# ── Феълҳо ───────────────────────────────────────────────────────────────────

def update_verb_form(verb_id: int, infinitive: str, present_stem: str,
                     past_stem: str, verb_class: str, root_name: str = ""):
    conn = get_connection()
    root_id = None
    if root_name:
        rrow = conn.execute(
            "SELECT id FROM roots WHERE lower(root) = ?", (root_name.lower(),)
        ).fetchone()
        root_id = rrow["id"] if rrow else None
    conn.execute(
        "UPDATE verb_forms SET infinitive=?, present_stem=?, past_stem=?,"
        " verb_class=?, root_id=? WHERE id=?",
        (infinitive.strip().lower(), present_stem, past_stem,
         verb_class, root_id, verb_id)
    )
    conn.commit()
    conn.close()


def delete_verb_form(verb_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM verb_forms WHERE id=?", (verb_id,))
    conn.commit()
    conn.close()
