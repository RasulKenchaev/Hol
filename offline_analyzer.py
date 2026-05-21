"""
Таҳлили офлайн — ду ҳолат:
  1. Ollama  — LLM-и маҳаллӣ (http://localhost:11434)
  2. Stats   — статистикаи SQL, бе ягон нармафзори иловагӣ
"""
import json
import re
import threading
import urllib.request
import urllib.error

import db

OLLAMA_URL = "http://localhost:11434"


# ══════════════════════════════════════════════════════════════
# Ollama — санҷиш ва рӯйхати моделҳо
# ══════════════════════════════════════════════════════════════

def is_ollama_running() -> bool:
    try:
        urllib.request.urlopen(OLLAMA_URL, timeout=2)
        return True
    except Exception:
        return False


def get_ollama_models() -> list[str]:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=3) as r:
            data = json.loads(r.read())
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def analyze_ollama(text: str, model: str, on_result, on_error,
                   lit_words: list[str] | None = None):
    """LLM-и маҳаллӣ тавассути Ollama REST API."""
    from ai_analyzer import SYSTEM_PROMPT, analyze_dialect as _build

    def _user_content() -> str:
        parts = [
            "═══════════════════════════════════════════════",
            "ВАЗИФА 1 — МУАЙЯНИ ЛАҲҶА",
            "═══════════════════════════════════════════════",
            f"Матн: «{text}»",
            "",
            "1. Лаҳҷаро муайян кун",
            "2. Далелҳоро шарҳ деҳ",
            "3. Ҷавоби равшан бидеҳ",
        ]
        if lit_words:
            lit_str = ", ".join(f"«{w}»" for w in lit_words)
            parts += [
                "",
                "═══════════════════════════════════════════════",
                "ВАЗИФА 2 — ТАҲЛИЛИ КАЛИМАҲОИ АДАБИИ ЁФТШУДА",
                "═══════════════════════════════════════════════",
                f"Калимаҳои адабии ёфтшуда: {lit_str}",
                "",
                "• Маъно ва ҷузъи нутқ",
                "• Мисоли истифода",
                "• Синоним (агар дошта бошад)",
            ]
        return "\n".join(parts)

    def _run():
        try:
            payload = json.dumps({
                "model": model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _user_content()},
                ],
            }, ensure_ascii=False).encode("utf-8")

            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            on_result(result["message"]["content"])

        except urllib.error.URLError:
            on_error(
                "Ollama кор намекунад.\n"
                "Насб кунед: https://ollama.com\n"
                "Сипас модел зеред:\n"
                "  ollama pull gemma3:4b"
            )
        except Exception as e:
            on_error(f"Ollama хато: {e}")

    threading.Thread(target=_run, daemon=True).start()


# ══════════════════════════════════════════════════════════════
# Статистикаи маҳаллӣ — SQL-асос, ҳамеша кор мекунад
# ══════════════════════════════════════════════════════════════

def analyze_stats(text: str, lit_words: list[str] | None = None) -> str:
    tokens = re.findall(r"[\wЀ-ӿ]+", text, re.UNICODE)
    if not tokens:
        return "Матн холӣ аст."

    scores, word_results = db.detect_dialect(tokens)
    meta = {d["key"]: d for d in db.get_dialects()}

    total = max(sum(scores.values()), 1)
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best, best_sc = ranked[0] if ranked else ("", 0)

    L = ["📊 ТАҲЛИЛИ МАҲАЛЛӢ (SQL-база)", "─" * 44, ""]

    if best_sc == 0:
        L.append("❌  Калимаҳои лаҳҷавӣ дар матн ёфт нашуданд.")
        L.append("    Луғатро пур кунед (＋ Калима илова).")
        return "\n".join(L)

    dm   = meta.get(best, {})
    conf = round(best_sc / total * 100)
    L.append(f"🏆  Лаҳҷаи пешбар: {dm.get('name', best)}")
    L.append(f"    Минтақа:  {dm.get('region', '—')}")
    L.append(f"    Эҳтимол:  {conf}%  ({best_sc} аз {len(tokens)} калима)")
    L.append("")

    matched = [(tok, m, wt) for tok, m, wt in word_results
               if m and wt in ("dialect", "both")]
    if matched:
        L.append("📝  Таҳлили калима ба калима:")
        for tok, mlist, _ in matched:
            lit    = db.find_literary(tok, mlist)
            pos    = db.get_pos(lit)
            names  = "، ".join(
                meta[m]["name"] for m in mlist if m in meta)
            lit_s  = f" → «{lit}»" if lit.lower() != tok.lower() else ""
            pos_s  = f" [{pos}]"   if pos and pos != "—"          else ""
            L.append(f"  • «{tok}»{pos_s}{lit_s}")
            L.append(f"    {names}")
        L.append("")

    unmatched = [tok for tok, m, _ in word_results if not m]
    if unmatched:
        preview = ", ".join(f"«{w}»" for w in unmatched[:8])
        dots    = "…" if len(unmatched) > 8 else ""
        L.append(f"❓  Шинохта нашуд ({len(unmatched)}): {preview}{dots}")
        L.append("")

    L.append("📊  Натиҷаҳо:")
    for dk, sc in ranked:
        if sc == 0:
            continue
        pct  = round(sc / total * 100)
        fill = round(pct / 5)
        bar  = "█" * fill + "░" * (20 - fill)
        name = meta.get(dk, {}).get("name", dk)
        L.append(f"    {name:22s}  {bar}  {pct:3d}%")

    L.append("")
    L.append(f"💡  Матн бештар ба {dm.get('name', best)} мансуб аст.")
    L.append(f"    ({dm.get('region', '')})")

    # ── Калимаҳои адабӣ ───────────────────────────────────────────────────
    if lit_words:
        L.append("")
        L.append("─" * 44)
        L.append("📚  КАЛИМАҲОИ АДАБИИ ЁФТШУДА:")
        L.append("─" * 44)
        for lw in sorted(lit_words):
            pos      = db.get_pos(lw)
            variants = db.find_variants(lw)
            pos_s    = f" [{pos}]" if pos and pos != "—" else ""
            L.append(f"  • «{lw}»{pos_s}  — адабии стандартӣ")
            if variants:
                v_items = list(variants.items())[:4]
                dots    = "…" if len(variants) > 4 else ""
                v_str   = ", ".join(
                    f"«{df}» ({meta.get(dk, {}).get('name', dk)})"
                    for dk, df in v_items
                )
                L.append(f"    └ лаҳҷавӣ: {v_str}{dots}")
        L.append("")

    return "\n".join(L)
