"""
Скрипти кӯчондан: dialect_data.json → dialect_data.db
Якбор иҷро кунед. Файли JSON дагал нест, нусхаи захиравӣ мемонад.
"""
import json
import os
import sys
import db

SRC = os.path.join(os.path.dirname(__file__), "dialect_data.json")
DST = os.path.join(os.path.dirname(__file__), "dialect_data.db")


def migrate():
    if not os.path.exists(SRC):
        print(f"❌  Файл ёфт нашуд: {SRC}")
        sys.exit(1)

    if os.path.exists(DST):
        ans = input(f"⚠   {DST} аллакай мавҷуд аст. Аз нав созем? (y/n): ").strip().lower()
        if ans != "y":
            print("Бекор карда шуд.")
            return
        os.remove(DST)
        print("Файли кӯҳна нест карда шуд.")

    print(f"📂  JSON хонда мешавад: {SRC}")
    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)

    print("🗄   SQLite ҷадвалҳо месозад…")
    db.init_db()

    dialects = data.get("dialects", {})
    word_pos  = data.get("word_pos", {})

    total_words    = 0
    total_phrases  = 0
    total_dialects = 0

    conn = db.get_connection()

    for order, (dk, dv) in enumerate(dialects.items()):
        name   = dv.get("name", dk)
        region = dv.get("region", "")
        conn.execute("""
            INSERT OR REPLACE INTO dialects (key, name, region, sort_order)
            VALUES (?, ?, ?, ?)
        """, (dk, name, region, order))
        total_dialects += 1

        for lit, form in dv.get("words", {}).items():
            pos = word_pos.get(lit.lower(), "")
            conn.execute("""
                INSERT INTO words (dialect_key, literary, dialect_form, category, pos)
                VALUES (?, ?, ?, 'words', ?)
            """, (dk, lit.strip().lower(), form.strip(), pos))
            total_words += 1

        for lit, form in dv.get("phrases", {}).items():
            pos = word_pos.get(lit.lower(), "")
            conn.execute("""
                INSERT INTO words (dialect_key, literary, dialect_form, category, pos)
                VALUES (?, ?, ?, 'phrases', ?)
            """, (dk, lit.strip().lower(), form.strip(), pos))
            total_phrases += 1

    conn.commit()
    conn.close()

    print()
    print("✅  Кӯчондан тамом шуд!")
    print(f"   Лаҳҷаҳо:  {total_dialects}")
    print(f"   Калимаҳо: {total_words:,}")
    print(f"   Ҷумлаҳо:  {total_phrases:,}")
    size_kb = os.path.getsize(DST) // 1024
    print(f"   Андозаи DB: {size_kb} КБ")
    print()
    print(f"📦  Нусхаи JSON ҳамон ҷо мемонад: {SRC}")
    print(f"🗄   Базаи нав: {DST}")

    # Санҷиш
    s = db.stats()
    print()
    print("📊  Омор:")
    print(f"   Ҷамъи калимаҳо дар DB: {s['total']:,}")
    for row in s["per_dialect"]:
        print(f"   {row['name']}: {row['cnt']:,}")


if __name__ == "__main__":
    migrate()
