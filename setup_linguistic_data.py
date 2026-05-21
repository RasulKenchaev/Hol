"""
Пур кардани ҷадвалҳои луғавии нав:
  • Вилоятҳо (4 та) ва пайванди ноҳияҳо ба вилоятҳо
  • Пешвандҳои стандартии тоҷикӣ
  • Пасвандҳои стандартии тоҷикӣ
  • Феълҳои маъмулии асосӣ

Иҷро: python setup_linguistic_data.py
"""
import db

# ══════════════════════════════════════════════════════════════════════════════
# 1. ВИЛОЯТҲО
# ══════════════════════════════════════════════════════════════════════════════

PROVINCES = [
    ("sugd",    "Вилояти Суғд",                   1),
    ("khatlon", "Вилояти Хатлон",                  2),
    ("rrs",     "Ноҳияҳои тобеи ҷумҳурӣ (РРС)",   3),
    ("vmkb",    "ВМКБ — Бадахшон",                 4),
]

# Пайванди ноҳия ба вилоят
DISTRICT_PROVINCE = {
    # ── Суғд ──────────────────────────────────────────────────────────────────
    "khujandi":    "sugd",
    "isfarai":     "sugd",
    "istaravsani": "sugd",
    "konibodomı":  "sugd",
    "bghafurovi":  "sugd",
    "mastchohi":   "sugd",
    "shahristoni": "sugd",
    "ashti":       "sugd",
    "zafarobodi":  "sugd",
    "jabborasulov":"sugd",
    "devashtichi": "sugd",
    "spitameni":   "sugd",
    "nuri_sugd":   "sugd",
    "panjakenti":  "sugd",
    # ── Хатлон ────────────────────────────────────────────────────────────────
    "kolabi":      "khatlon",
    "bokhtari":    "khatlon",
    "yavoni":      "khatlon",
    "vakhshi":     "khatlon",
    "dangarai":    "khatlon",
    "vosei":       "khatlon",
    "balchjuvoni": "khatlon",
    "farhori":     "khatlon",
    "muuminobodi": "khatlon",
    "temurmaliki": "khatlon",
    "khovalingi":  "khatlon",
    "shuroboди":   "khatlon",
    "kumsangiri":  "khatlon",
    "jillikoli":   "khatlon",
    "kubodioni":   "khatlon",
    "nosirikhusrav":"khatlon",
    "nureki":      "khatlon",
    "pirмasti":    "khatlon",
    "rumi":        "khatlon",
    "khuroson":    "khatlon",
    "levakanт":    "khatlon",
    # ── РРС ───────────────────────────────────────────────────────────────────
    "garmi":       "rrs",
    "rashti":      "rrs",
    "hisori":      "rrs",
    "varzobi":     "rrs",
    "vahdati":     "rrs",
    "rudaki":      "rrs",
    "tursunzoda":  "rrs",
    "shahrinavi":  "rrs",
    "fayzobodi":   "rrs",
    "nurobodi":    "rrs",
    "tavildara":   "rrs",
    "lakhshi":     "rrs",
    "dushanbe":    "rrs",
    # ── ВМКБ ──────────────────────────────────────────────────────────────────
    "badakhshoni": "vmkb",
    "darvozi":     "vmkb",
    "shughnoni":   "vmkb",
    "rushoni":     "vmkb",
    "yazgulomi":   "vmkb",
    "vanji":       "vmkb",
    "ishkoshimi":  "vmkb",
    "murgobi":     "vmkb",
    "roshtqalai":  "vmkb",
    "bartangi":    "vmkb",
    "shakhdaroi":  "vmkb",
}

# ══════════════════════════════════════════════════════════════════════════════
# 2. ПЕШВАНДҲО
# (prefix, maʿno, toifa)
# ══════════════════════════════════════════════════════════════════════════════

PREFIXES = [
    # Инкор
    ("на-",     "Инкор, нафӣ",                    "negation"),
    ("ни-",     "Инкор (шакли кӯҳна)",             "negation"),
    ("бе-",     "Бе, бидуни, фоқид аз",            "privative"),
    ("нобе-",   "Нобудӣ, набудан",                  "privative"),
    # Феъл
    ("ме-",     "Замони ҳозира/оянда",              "verbal_pres"),
    ("мебо-",   "Шакли ёридиҳандаи ҳозира",        "verbal_pres"),
    ("мена-",   "Инкори ҳозира/оянда",              "verbal_neg"),
    ("намео-",  "Инкори замони ҳозира",             "verbal_neg"),
    ("наме-",   "Инкори ҳозира (кӯтоҳ)",           "verbal_neg"),
    # Пешбурди маъно
    ("ба-",     "Ба, дар, суи",                     "directional"),
    ("бо-",     "Бо, ҳамроҳ",                       "comitative"),
    ("ҳам-",    "Бо ҳам, якҷоя",                    "comitative"),
    ("ҳамо-",   "Ҳамон, худи он",                   "identical"),
    ("со-",     "Соз- (аз форсӣ)",                  "causative"),
    # Вақт
    ("пеш-",    "Пеш аз, пешина",                   "temporal"),
    ("баъд-",   "Баъд аз, пасина",                   "temporal"),
    ("навин-",  "Нав, тоза",                          "quality"),
    # Давраи нав
    ("нек-",    "Нек, хуб, хайр",                   "positive"),
    ("бад-",    "Бад, зишт",                          "negative"),
    ("ком-",    "Кам, каме",                          "diminutive"),
    ("пур-",    "Пур, зиёд",                          "augmentative"),
    ("фар-",    "Поён, берун (аз авестоӣ)",           "directional"),
    # Интернатсионалӣ дар тоҷикӣ
    ("ре-",     "Такрор (аз лотинӣ)",                "repetitive"),
    ("мега-",   "Бузург (аз юнонӣ)",                  "augmentative"),
    ("мини-",   "Хурд (аз лотинӣ)",                  "diminutive"),
]

# ══════════════════════════════════════════════════════════════════════════════
# 3. ПАСВАНДҲО
# (suffix, maʿno, toifa, pos_from, pos_to)
# ══════════════════════════════════════════════════════════════════════════════

SUFFIXES = [
    # ── Ҷамъ ──────────────────────────────────────────────────────────────────
    ("-ҳо",    "Ҷамъи умумӣ",                      "plural",     "noun",      "noun"),
    ("-он",    "Ҷамъи одамон",                      "plural",     "noun",      "noun"),
    ("-ён",    "Ҷамъи (-а/-е/-и) анҷом)",           "plural",     "noun",      "noun"),
    ("-гон",   "Ҷамъи (-а/-о) анҷом",               "plural",     "noun",      "noun"),
    ("-ат",    "Ҷамъи (аз арабӣ)",                  "plural_ar",  "noun",      "noun"),
    # ── Соҳибӣ ────────────────────────────────────────────────────────────────
    ("-ам",    "Соҳибии 1 шахси танҳо",              "poss_1sg",   "noun",      "noun"),
    ("-ат",    "Соҳибии 2 шахси танҳо",              "poss_2sg",   "noun",      "noun"),
    ("-аш",    "Соҳибии 3 шахси танҳо",              "poss_3sg",   "noun",      "noun"),
    ("-амон",  "Соҳибии 1 шахси ҷамъ",              "poss_1pl",   "noun",      "noun"),
    ("-атон",  "Соҳибии 2 шахси ҷамъ",              "poss_2pl",   "noun",      "noun"),
    ("-ашон",  "Соҳибии 3 шахси ҷамъ",              "poss_3pl",   "noun",      "noun"),
    # ── Ҳолат ─────────────────────────────────────────────────────────────────
    ("-ро",    "Ҳолати бевоситаи объект",            "accusative", "noun",      "noun"),
    ("-е",     "Нишонаи ноёбии (indefinite)",        "indefinite", "noun",      "noun"),
    ("-и",     "Пайванди изофӣ (эзофа)",             "genitive",   "noun",      "noun"),
    # ── Сифатӣ ────────────────────────────────────────────────────────────────
    ("-ӣ",     "Нисбатӣ, сифати нисбӣ",             "adjective",  "noun",      "adjective"),
    ("-она",   "Ба тарзи, ба монанд",               "adjective",  "noun",      "adverb"),
    ("-вор",   "Монанди, ба шакли",                  "adjective",  "noun",      "adjective"),
    ("-нок",   "Пур аз, дорандаи",                   "adjective",  "noun",      "adjective"),
    ("-манд",  "Соҳиби, дорандаи",                   "adjective",  "noun",      "adjective"),
    ("-зор",   "Майдон, ҷои зиёди…",                "adjective",  "noun",      "noun"),
    ("-истон", "Сарзамини, ҷои",                     "locative",   "noun",      "noun"),
    ("-хона",  "Ҷой, биноӣ барои",                   "locative",   "noun",      "noun"),
    ("-гоҳ",   "Ҷой, маҳал барои",                   "locative",   "noun",      "noun"),
    # ── Исмӣ (агентӣ) ─────────────────────────────────────────────────────────
    ("-гар",   "Касби кунандаи кор",                 "agentive",   "noun",      "noun"),
    ("-кор",   "Кунандаи касб",                      "agentive",   "noun",      "noun"),
    ("-бон",   "Нигаҳбон, парастор",                 "agentive",   "noun",      "noun"),
    ("-дор",   "Нигаҳдорандаи",                      "agentive",   "noun",      "noun"),
    ("-ист",   "Мансуб ба (мутахассис)",             "agentive",   "noun",      "noun"),
    ("-ча",    "Тасғир (хурд кардан)",               "diminutive", "noun",      "noun"),
    ("-дон",   "Зарфи нигоҳдорӣ",                   "container",  "noun",      "noun"),
    # ── Феълӣ (шахсӣ) ─────────────────────────────────────────────────────────
    ("-ам",    "Феъл: 1 шахс танҳо, ҳозира",        "verb_1sg",   "verb",      "verb"),
    ("-ӣ",     "Феъл: 2 шахс танҳо, ҳозира",        "verb_2sg",   "verb",      "verb"),
    ("-ад",    "Феъл: 3 шахс танҳо, ҳозира",        "verb_3sg",   "verb",      "verb"),
    ("-ем",    "Феъл: 1 шахс ҷамъ, ҳозира",         "verb_1pl",   "verb",      "verb"),
    ("-ед",    "Феъл: 2 шахс ҷамъ, ҳозира",         "verb_2pl",   "verb",      "verb"),
    ("-анд",   "Феъл: 3 шахс ҷамъ, ҳозира",         "verb_3pl",   "verb",      "verb"),
    # ── Масдар ────────────────────────────────────────────────────────────────
    ("-идан",  "Масдари I (инфинитив)",              "infinitive", "verb",      "verb"),
    ("-дан",   "Масдари II (инфинитив)",              "infinitive", "verb",      "verb"),
    ("-тан",   "Масдари III (инфинитив)",             "infinitive", "verb",      "verb"),
    # ── Мафъул ────────────────────────────────────────────────────────────────
    ("-а",     "Мафъули феъл (participle)",          "participle", "verb",      "adjective"),
    ("-агӣ",   "Ҳолат, вазъ",                        "state",      "verb",      "noun"),
    ("-иш",    "Исми феъл (масдари кӯтоҳ)",          "gerund",     "verb",      "noun"),
    ("-ӣ",     "Исми феъл (маъно)",                  "gerund",     "verb",      "noun"),
    # ── Зарф ──────────────────────────────────────────────────────────────────
    ("-она",   "Ба тарз/шакли (зарф)",              "adverb",     "adjective", "adverb"),
    ("-тар",   "Сифати муқоисавӣ",                   "comparative","adjective", "adjective"),
    ("-тарин", "Сифати оливӣ",                       "superlative","adjective", "adjective"),
]

# ══════════════════════════════════════════════════════════════════════════════
# 4. ФЕЪЛҲОИ МАЪМУЛИИ АСОСӢ
# (infinitive, present_stem, past_stem, verb_class, root_word)
# ══════════════════════════════════════════════════════════════════════════════

VERBS = [
    ("рафтан",    "рав",    "рафт",   "I",  "рав"),
    ("омадан",    "о",      "омад",   "I",  "о"),
    ("кардан",    "кун",    "кард",   "I",  "кун"),
    ("гуфтан",    "гӯ",     "гуфт",   "I",  "гӯ"),
    ("хондан",    "хон",    "хонд",   "I",  "хон"),
    ("нишастан",  "нишин",  "нишаст", "I",  "нишин"),
    ("хӯрдан",    "хӯр",    "хӯрд",   "I",  "хӯр"),
    ("нӯшидан",   "нӯш",    "нӯшид",  "II", "нӯш"),
    ("дидан",     "бин",    "дид",    "I",  "бин"),
    ("шунидан",   "шунав",  "шунид",  "II", "шунав"),
    ("донистан",  "дон",    "донист", "I",  "дон"),
    ("хостан",    "хоҳ",    "хост",   "I",  "хоҳ"),
    ("тавонистан","тавон",  "тавонист","I", "тавон"),
    ("будан",     "бош",    "буд",    "irr","бош"),
    ("шудан",     "шав",    "шуд",    "I",  "шав"),
    ("доштан",    "дор",    "дошт",   "I",  "дор"),
    ("гирифтан",  "гир",    "гирифт", "I",  "гир"),
    ("додан",     "деҳ",    "дод",    "I",  "деҳ"),
    ("овардан",   "овар",   "овард",  "I",  "овар"),
    ("бурдан",    "бар",    "бурд",   "I",  "бар"),
    ("навиштан",  "навис",  "навишт", "I",  "навис"),
    ("расидан",   "рас",    "расид",  "II", "рас"),
    ("мондан",    "мон",    "монд",   "I",  "мон"),
    ("задан",     "зан",    "зад",    "I",  "зан"),
    ("пурсидан",  "пурс",   "пурсид", "II", "пурс"),
    ("фаҳмидан",  "фаҳм",   "фаҳмид", "II", "фаҳм"),
    ("гуфтугӯ кардан", "кун", "кард", "I", "кун"),
    ("истодан",   "истод",  "истод",  "irr","истод"),
    ("нишонидан", "нишон",  "нишонид","II", "нишон"),
    ("пӯшидан",   "пӯш",    "пӯшид",  "II", "пӯш"),
]


# ══════════════════════════════════════════════════════════════════════════════
def main():
    db.init_db()

    print("═" * 54)
    print("   ПУРКУНИИ БАЗАИ ЛУҒАВИИ ТОҶИКӢ")
    print("═" * 54)

    # 1. Вилоятҳо
    print("\n1. Вилоятҳо:")
    prov_added = 0
    for key, name, order in PROVINCES:
        if db.add_province(key, name, order):
            prov_added += 1
            print(f"   ✔ {name}")
    print(f"   Ҷамъ: {prov_added} вилоят")

    # 2. Пайванди ноҳияҳо ба вилоятҳо
    print("\n2. Пайванди ноҳияҳо ба вилоятҳо:")
    all_dialects = {d["key"] for d in db.get_dialects()}
    linked = 0
    for dk, pk in DISTRICT_PROVINCE.items():
        if dk in all_dialects:
            db.link_to_province(dk, pk)
            linked += 1
    print(f"   ✔ {linked} ноҳия пайваст шуд")

    # 3. Пешвандҳо
    print("\n3. Пешвандҳо:")
    pref_added = pref_updated = 0
    for pref, meaning, cat in PREFIXES:
        s = db.add_prefix(pref, meaning, cat)
        if s == "added":    pref_added   += 1
        elif s == "updated": pref_updated += 1
    print(f"   ✔ {pref_added} нав  |  {pref_updated} навсозӣ")

    # 4. Пасвандҳо
    print("\n4. Пасвандҳо:")
    suf_added = suf_updated = 0
    for suf, meaning, cat, pos_from, pos_to in SUFFIXES:
        s = db.add_suffix(suf, meaning, cat, pos_from, pos_to)
        if s == "added":    suf_added   += 1
        elif s == "updated": suf_updated += 1
    print(f"   ✔ {suf_added} нав  |  {suf_updated} навсозӣ")

    # 5. Феълҳо (реша + шакл)
    print("\n5. Феълҳои асосӣ:")
    verb_added = 0
    for inf, pres, past, vclass, root_w in VERBS:
        # Аввал решаро илова кун
        db.add_root(root_w, "феъл")
        s = db.add_verb_form(inf, pres, past, vclass, root_w)
        if s == "added":
            verb_added += 1
    print(f"   ✔ {verb_added} феъл")

    # Натиҷа
    print()
    print("═" * 54)
    conn = db.get_connection()
    t_prov = conn.execute("SELECT COUNT(*) FROM provinces").fetchone()[0]
    t_pref = conn.execute("SELECT COUNT(*) FROM prefixes").fetchone()[0]
    t_suf  = conn.execute("SELECT COUNT(*) FROM suffixes").fetchone()[0]
    t_root = conn.execute("SELECT COUNT(*) FROM roots").fetchone()[0]
    t_vf   = conn.execute("SELECT COUNT(*) FROM verb_forms").fetchone()[0]
    t_poly = conn.execute("SELECT COUNT(*) FROM polysemy").fetchone()[0]
    conn.close()

    print(f"   Вилоятҳо:   {t_prov}")
    print(f"   Пешвандҳо:  {t_pref}")
    print(f"   Пасвандҳо:  {t_suf}")
    print(f"   Решаҳо:     {t_root}")
    print(f"   Феълҳо:     {t_vf}")
    print(f"   Сермаъноӣ:  {t_poly}")
    print("═" * 54)
    print("   Тамом!")
    print()
    print("   Барои идоракунии решаҳо/феълҳо/сермаъноӣ:")
    print("   python manage_linguistic.py")


if __name__ == "__main__":
    main()
