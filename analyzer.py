"""
Таҳлилгари матни лаҳҷавӣ — мустақил аз UI.
Ҳам Tkinter ва ҳам Kivy истифода мебаранд.
"""
import re
import db


def tokenize(text: str) -> list[tuple[str, bool]]:
    """Матнро ба [(token, is_word)] тақсим мекунад."""
    result = []
    for m in re.finditer(
        r"[\wЀ-ӿ]+(?:-[\wЀ-ӿ]+)*|[^\wЀ-ӿ\n]+|\n", text, re.UNICODE
    ):
        tok = m.group()
        is_word = bool(re.match(r"^[\wЀ-ӿ]+(?:-[\wЀ-ӿ]+)*$", tok, re.UNICODE))
        result.append((tok, is_word))
    return result


def analyze_text(text: str) -> dict:
    """
    Матнро таҳлил мекунад.
    Бармегардонад:
      scores       – {dialect_key: score}
      wr_map       – {token_lower: (matched_dialects, wtype, lit_override)}
      tokens       – [(tok, is_word)] тартиби матн
      best         – калиди беҳтарин лаҳҷа
      best_name    – номи беҳтарин лаҳҷа
      best_pct     – фоизи беҳтарин лаҳҷа
      dialects_meta – {key: dialect_dict}
    """
    if not text.strip():
        return {
            "scores": {}, "wr_map": {}, "tokens": [],
            "best": "", "best_name": "", "best_pct": 0,
            "dialects_meta": {},
        }

    compound_tokens = re.findall(r"[\wЀ-ӿ]+(?:-[\wЀ-ӿ]+)+", text, re.UNICODE)
    simple_tokens   = re.findall(r"[\wЀ-ӿ]+", text, re.UNICODE)

    scores, word_results = db.detect_dialect(simple_tokens)

    unknown_toks = [tok for tok, m, _ in word_results if not m]
    morph_map    = db.morph_classify(unknown_toks)

    wr_map: dict[str, tuple] = {}
    for tok, m, wtype in word_results:
        wr_map.setdefault(tok.lower(), (m, wtype, None))

    for tl, (dks, lit_f, mtype) in morph_map.items():
        wr_map[tl] = (dks, mtype, lit_f)
        if "dialect" in mtype:
            for dk in dks:
                scores[dk] = scores.get(dk, 0) + 1

    for comp in compound_tokens:
        tl = comp.lower()
        if tl in wr_map:
            continue
        parts    = comp.split("-")
        all_m:   list[str] = []
        wt_best  = "unknown"
        lit_best = None
        for p in parts:
            pm, pwt, plit = wr_map.get(p.lower(), ([], "unknown", None))
            for dk in pm:
                if dk not in all_m:
                    all_m.append(dk)
            if pwt not in ("unknown", "literary_stem") and wt_best == "unknown":
                wt_best  = pwt
                lit_best = plit
        if all_m:
            wr_map[tl] = (all_m, wt_best or "dialect", lit_best)

    for tl in list(wr_map.keys()):
        if wr_map[tl][0]:
            continue
        corrected = db.correct_elision(tl)
        if corrected and corrected != tl:
            wr_map[tl] = ([], "elision_corrected", corrected)

    total    = max(sum(scores.values()), 1)
    best     = max(scores, key=lambda k: scores[k]) if scores else ""
    best_pct = round(scores.get(best, 0) / total * 100) if best else 0

    dialects_meta = {d["key"]: d for d in db.get_dialects()}
    best_name     = dialects_meta.get(best, {}).get("name", "") if best else ""

    return {
        "scores":        scores,
        "wr_map":        wr_map,
        "tokens":        tokenize(text),
        "best":          best,
        "best_name":     best_name,
        "best_pct":      best_pct,
        "total":         total,
        "dialects_meta": dialects_meta,
    }


def build_markup(tokens: list, wr_map: dict) -> str:
    """
    Матнро ба Kivy markup ([[color=xxx]...[/color]]) табдил медиҳад.
    Рангҳо:
      сиёҳ    (#e0e0e0 дар dark) — адабӣ
      сурх    (#ef5350)          — лаҳҷавӣ (1 ноҳия)
      кабуд   (#42a5f5)          — сермаъно (якчанд ноҳия)
      норинҷӣ (#ffa726)          — морфологӣ
      сабз    (#66bb6a)          — ислоҳшуда
    """
    _STD = ["ашон", "амон", "атон", "анд", "ям", "ем", "ед",
            "ам", "ат", "аш", "ро", "ҳо", "он"]
    _CORR = {"м": "ам", "т": "ат", "ш": "аш", "д": "ад"}

    CLit  = "e0e0e0"
    CDial = "ef5350"
    CMany = "42a5f5"
    CMorf = "ffa726"
    CCorr = "66bb6a"

    parts = []
    for tok, is_word in tokens:
        if tok == "\n":
            parts.append("\n")
            continue
        if not is_word:
            parts.append(tok.replace("[", "&#91;").replace("]", "&#93;"))
            continue

        matched, wtype, lit_ov = wr_map.get(tok.lower(), ([], "unknown", None))
        safe = tok.replace("[", "&#91;").replace("]", "&#93;")

        if wtype == "elision_corrected":
            last = tok[-1].lower()
            if last in _CORR:
                root_s = tok[:-1].replace("[", "&#91;").replace("]", "&#93;")
                suf_s  = tok[-1]
                parts.append(
                    f"[color={CCorr}][b]{root_s}[/b][/color]"
                    f"[color={CDial}][b]{suf_s}[/b][/color]"
                )
            else:
                parts.append(f"[color={CCorr}][b]{safe}[/b][/color]")
            continue

        if not matched:
            parts.append(f"[color={CLit}]{safe}[/color]")
            continue

        if wtype in ("literary", "literary_stem"):
            parts.append(f"[color={CLit}]{safe}[/color]")
        elif wtype in ("dialect", "dialect_stem", "both"):
            col  = CDial if len(matched) == 1 else CMany
            tl   = tok.lower()
            suf  = next(
                (s for s in _STD if tl.endswith(s) and len(tl) > len(s) + 1), ""
            ) if wtype not in ("literary", "literary_stem") else ""
            if suf:
                root_s = tok[:-len(suf)].replace("[", "&#91;")
                suf_s  = tok[-len(suf):]
                parts.append(
                    f"[color={col}][b]{root_s}[/b][/color]"
                    f"[color={CLit}]{suf_s}[/color]"
                )
            else:
                parts.append(f"[color={col}][b]{safe}[/b][/color]")
        else:
            parts.append(f"[color={CMorf}]{safe}[/color]")

    return "".join(parts)
