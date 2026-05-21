"""
Тозакунии база — се вариант:

  1  — Танҳо калимаҳоро тоза кун (ноҳияҳо мемонанд)
  2  — Ҳама чизро тоза кун (ноҳияҳо ҳам нест мешаванд)
  3  — Аз JSON-и захиравӣ барқарор кун (dialect_data.json)
"""
import os, sys, json
import db

DB_FILE  = os.path.join(os.path.dirname(__file__), "dialect_data.db")
JSON_BAK = os.path.join(os.path.dirname(__file__), "dialect_data.json")


def confirm(msg: str) -> bool:
    ans = input(f"⚠   {msg}  (y/n): ").strip().lower()
    return ans == "y"


def opt1_clear_words():
    """Калимаҳоро нест кун, ноҳияҳо мемонанд."""
    conn = db.get_connection()
    cnt  = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
    conn.close()
    if not confirm(f"Ҳамаи {cnt:,} калима нест карда мешавад. Ноҳияҳо мемонанд. Давом?"):
        print("Бекор.")
        return
    conn = db.get_connection()
    conn.execute("DELETE FROM words")
    conn.commit()
    conn.close()
    print(f"✅  {cnt:,} калима нест карда шуд.")
    print("    Ноҳияҳо:", len(db.get_dialects()), "та")


def opt2_full_reset():
    """Ҳама чизро нест кун — файли DB-ро нест мекунем."""
    if not confirm("ҲАМА ЧИЗ нест карда мешавад: ноҳияҳо, калимаҳо, ҷузъи нутқ. Давом?"):
        print("Бекор.")
        return
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"✅  {DB_FILE} нест карда шуд.")
    db.init_db()
    print("    База аз нав сохта шуд (холӣ).")
    print("    Акнун метавонед ноҳияҳоро дастӣ илова кунед ё add_all_districts.py-ро иҷро кунед.")


def opt3_restore_from_json():
    """Аз нусхаи захиравии JSON барқарор кун."""
    if not os.path.exists(JSON_BAK):
        print(f"❌  Файли захиравӣ ёфт нашуд: {JSON_BAK}")
        return
    if not confirm("Базаи кунунӣ пурра нест ва аз JSON барқарор мешавад. Давом?"):
        print("Бекор.")
        return

    # Нест кардан ва аз нав сохтан
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    db.init_db()

    print(f"📂  JSON хонда мешавад: {JSON_BAK}")
    with open(JSON_BAK, encoding="utf-8") as f:
        data = json.load(f)

    word_pos = data.get("word_pos", {})
    conn     = db.get_connection()
    total_w  = 0
    total_p  = 0

    for order, (dk, dv) in enumerate(data.get("dialects", {}).items()):
        conn.execute(
            "INSERT OR REPLACE INTO dialects (key, name, region, sort_order) VALUES (?,?,?,?)",
            (dk, dv.get("name", dk), dv.get("region", ""), order)
        )
        for lit, form in dv.get("words", {}).items():
            pos = word_pos.get(lit.lower(), "")
            conn.execute(
                "INSERT INTO words (dialect_key, literary, dialect_form, category, pos)"
                " VALUES (?,?,?,?,?)",
                (dk, lit.strip().lower(), form.strip(), "words", pos)
            )
            total_w += 1
        for lit, form in dv.get("phrases", {}).items():
            pos = word_pos.get(lit.lower(), "")
            conn.execute(
                "INSERT INTO words (dialect_key, literary, dialect_form, category, pos)"
                " VALUES (?,?,?,?,?)",
                (dk, lit.strip().lower(), form.strip(), "phrases", pos)
            )
            total_p += 1

    conn.commit()
    conn.close()

    print(f"✅  Барқарор шуд!")
    print(f"   Лаҳҷаҳо:  {len(data['dialects'])}")
    print(f"   Калимаҳо: {total_w:,}")
    print(f"   Ҷумлаҳо:  {total_p:,}")
    print()
    print("   Барои ноҳияҳои иловагӣ: python add_all_districts.py")


# ══════════════════════════════════════════════════════════════
def main():
    print()
    print("═" * 50)
    print("   ТОЗАКУНИИ БАЗАИ ЛАҲҶАҲО")
    print("═" * 50)

    s = db.stats()
    print(f"   Ҳолати кунунӣ: {len(db.get_dialects())} ноҳия, {s['total']:,} калима")
    print()
    print("   1  — Танҳо калимаҳоро тоза кун (ноҳияҳо мемонанд)")
    print("   2  — Ҳама чизро тоза кун (аз нол оғоз)")
    print("   3  — Аз JSON-и захиравӣ барқарор кун")
    print("   0  — Бекор кун")
    print()

    choice = input("   Интихоб: ").strip()
    print()

    if choice == "1":
        opt1_clear_words()
    elif choice == "2":
        opt2_full_reset()
    elif choice == "3":
        opt3_restore_from_json()
    else:
        print("Бекор карда шуд.")


if __name__ == "__main__":
    main()
