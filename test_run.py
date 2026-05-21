from translator import load_data, translate_phrase

data = load_data()
print("Барнома кор мекунад!")
print("Лаҳҷаҳо:", list(data["dialects"].keys()))
print()

tests = ["Ман меравам", "Намедонам", "Падар ба хона омадам"]

for dialect_key in ["gharmi", "kulobi", "khujandi", "badakhshani"]:
    name = data["dialects"][dialect_key]["name"]
    print(f"=== {name} ===")
    for t in tests:
        result = translate_phrase(t, dialect_key, data)
        print(f"  {t:30} -> {result}")
    print()

print("Тамом! Барнома омода аст.")
