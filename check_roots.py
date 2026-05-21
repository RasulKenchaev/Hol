import db

conn = db.get_connection()

# Феълҳо
vf = conn.execute(
    "SELECT infinitive, present_stem, past_stem, verb_class FROM verb_forms LIMIT 30"
).fetchall()
print("=== VERB_FORMS ===")
for v in vf:
    print(f"  {v['infinitive']:16} pres={v['present_stem']:10} past={v['past_stem']:10}")

total_vf = conn.execute("SELECT COUNT(*) as c FROM verb_forms").fetchone()["c"]
print(f"  Jami: {total_vf}")

# Калимахои лахчави (намунаи аввал)
ws = conn.execute(
    "SELECT literary, dialect_form, dialect_key FROM words ORDER BY literary LIMIT 30"
).fetchall()
print()
print("=== WORDS (namuna) ===")
for w in ws:
    print(f"  {w['literary']:20} <- {w['dialect_form']:20} [{w['dialect_key']}]")
total_w = conn.execute("SELECT COUNT(*) as c FROM words").fetchone()["c"]
print(f"  Jami: {total_w}")

conn.close()

# Sanjiши мушкилотнок
print()
print("=== MUAMMOHО ===")
tests = [
    ("мерам",    "меравам"),
    ("хондем",   "хондем"),
    ("гуфтему",  "гуфтем"),
    ("рафтему",  "рафтем"),
    ("дидам",    "дидам"),
    ("омадам",   "омадам"),
    ("истодам",  "истодам"),
    ("мегӯям",   "мегӯям"),
    ("мехонам",  "мехонам"),
    ("нахондем", "нахондем"),
]
for word, expected in tests:
    r = db.morph_analyze_word(word)
    rec = r["literary_reconstruction"]
    ok = "OK" if rec == expected else "??"
    print(f"  {ok} {word:16} -> {rec:20} (kutish: {expected})")
