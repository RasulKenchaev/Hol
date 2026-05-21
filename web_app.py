import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, render_template, request, jsonify
import db

API_KEY_FILE = os.path.join(os.path.dirname(__file__), ".api_key")

app = Flask(__name__)
db.init_db()


@app.route("/")
def index():
    dialects = db.get_dialects()
    return render_template("index.html", dialects=dialects)


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    text = (request.json or {}).get("text", "").strip()
    if not text:
        return jsonify({"error": "empty"})

    tokens = re.findall(r"[\wЀ-ӿ]+", text, re.UNICODE)
    scores, word_results = db.detect_dialect(tokens)

    total   = max(sum(scores.values()), 1)
    best    = max(scores, key=lambda k: scores[k]) if scores else ""
    best_sc = scores.get(best, 0)

    dialects_meta = {d["key"]: d for d in db.get_dialects()}

    results = []
    for dk, cnt in scores.items():
        if dk not in dialects_meta:
            continue
        results.append({
            "key":    dk,
            "name":   dialects_meta[dk]["name"],
            "region": dialects_meta[dk]["region"],
            "score":  cnt,
            "pct":    round(cnt / total * 100),
        })
    results.sort(key=lambda r: r["score"], reverse=True)

    winner = None
    if best and best_sc > 0 and best in dialects_meta:
        dm = dialects_meta[best]
        winner = {"key": best, "name": dm["name"], "region": dm["region"]}

    return jsonify({
        "results":      results,
        "word_results": [{"word": w, "dialects": m} for w, m in word_results],
        "winner":       winner,
        "best_score":   best_sc,
        "total":        total,
    })


@app.route("/api/ai_analyze", methods=["POST"])
def api_ai_analyze():
    body    = request.json or {}
    text    = body.get("text", "").strip()
    api_key = body.get("api_key", "").strip()
    if not api_key and os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, encoding="utf-8") as f:
            api_key = f.read().strip()
    if not text:
        return jsonify({"error": "Матн холӣ аст"})
    if not api_key:
        return jsonify({"error": "Калиди API лозим аст"})
    try:
        import anthropic
        from ai_analyzer import SYSTEM_PROMPT
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content":
                f"Матни зеринро таҳлил кун ва муайян намо ки ба кадом лаҳҷа мансуб аст.\n\n"
                f"Матн: «{text}»\n\n"
                f"1. Лаҳҷаро муайян кун\n2. Далелҳоро шарҳ деҳ\n3. Ҷавоби равшан бидеҳ"
            }]
        )
        return jsonify({"result": msg.content[0].text})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/add_word", methods=["POST"])
def api_add_word():
    body = request.json or {}
    dk   = body.get("dialect", "")
    lit  = body.get("literary", "").strip()
    dial = body.get("dialect_word", "").strip()
    cat  = body.get("type", "words")
    pos  = body.get("pos", "")
    if not dk or not lit or not dial:
        return jsonify({"ok": False, "error": "Маълумот нопурра"})
    dialects = {d["key"] for d in db.get_dialects()}
    if dk not in dialects:
        return jsonify({"ok": False, "error": "Лаҳҷа ёфт нашуд"})
    status = db.add_word(dk, lit, dial, cat, pos)
    return jsonify({"ok": status in ("added", "updated"), "status": status})


@app.route("/api/stats", methods=["GET"])
def api_stats():
    return jsonify(db.stats())


if __name__ == "__main__":
    host = "0.0.0.0"
    port = 5050
    print(f"\n  Барнома дар: http://localhost:{port}")
    print(f"  Аз телефон:  http://<IP-компютер>:{port}\n")
    app.run(host=host, port=port, debug=False)
