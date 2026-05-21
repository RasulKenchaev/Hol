"""
Воситаи илова кардани калимаҳои нав ба луғат.
Run: python add_words.py
"""
import json
import os

DATA_FILE = os.path.join(os.path.dirname(__file__), "dialect_data.json")


def load():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_dialects(data):
    print("\nЛаҳҷаҳои мавҷуда:")
    for i, (k, v) in enumerate(data["dialects"].items(), 1):
        print(f"  {i}. {v['name']} ({k})")


def main():
    data = load()
    print("=" * 50)
    print("  Воситаи илова кардани калима ба луғат")
    print("=" * 50)

    while True:
        print("\nАмалиёт:")
        print("  1. Калимаи нав илова кун")
        print("  2. Ҷумлаи нав илова кун")
        print("  3. Луғатро намоиш деҳ")
        print("  4. Хуруҷ")
        choice = input("Интихоб (1-4): ").strip()

        if choice == "1":
            list_dialects(data)
            dial_keys = list(data["dialects"].keys())
            try:
                idx = int(input("Рақами лаҳҷа: ")) - 1
                key = dial_keys[idx]
            except (ValueError, IndexError):
                print("Рақам нодуруст!")
                continue

            literary = input("Калимаи адабӣ: ").strip().lower()
            dialect_word = input(f"Дар лаҳҷаи {data['dialects'][key]['name']}: ").strip()

            data["dialects"][key]["words"][literary] = dialect_word
            save(data)
            print(f"✓ Илова шуд: '{literary}' → '{dialect_word}'")

        elif choice == "2":
            list_dialects(data)
            dial_keys = list(data["dialects"].keys())
            try:
                idx = int(input("Рақами лаҳҷа: ")) - 1
                key = dial_keys[idx]
            except (ValueError, IndexError):
                print("Рақам нодуруст!")
                continue

            literary = input("Ҷумлаи адабӣ: ").strip().lower()
            dialect_phrase = input(f"Дар лаҳҷаи {data['dialects'][key]['name']}: ").strip()

            data["dialects"][key]["phrases"][literary] = dialect_phrase
            save(data)
            print(f"✓ Илова шуд: '{literary}' → '{dialect_phrase}'")

        elif choice == "3":
            list_dialects(data)
            dial_keys = list(data["dialects"].keys())
            try:
                idx = int(input("Рақами лаҳҷа: ")) - 1
                key = dial_keys[idx]
            except (ValueError, IndexError):
                print("Рақам нодуруст!")
                continue

            d = data["dialects"][key]
            print(f"\n--- {d['name']} ---")
            print("Калимаҳо:")
            for k, v in d["words"].items():
                print(f"  {k:20} → {v}")
            print("Ҷумлаҳо:")
            for k, v in d["phrases"].items():
                print(f"  {k:30} → {v}")

        elif choice == "4":
            print("Хайр!")
            break
        else:
            print("Интихоби нодуруст")


if __name__ == "__main__":
    main()
