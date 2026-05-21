import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os, re
import db
from importer import import_excel, import_word, create_template_excel
from ai_analyzer import analyze_dialect
import offline_analyzer
import manage_linguistic
import tajik_keys
import updater
import license as lic

API_KEY_FILE    = os.path.join(os.path.dirname(__file__), ".api_key")
_CONTACT_FILE   = os.path.join(os.path.dirname(__file__), ".admin_contact")
_CONTACT_DEFAULT = {
    "name":  "Холмуродов Раҷабали",
    "email": "jeki-102011@mail.ru",
    "phone": "+992 93 476-15-15",
}

def _load_contact() -> dict:
    import json
    try:
        with open(_CONTACT_FILE, encoding="utf-8") as f:
            d = json.load(f)
        return {**_CONTACT_DEFAULT, **d}
    except Exception:
        return dict(_CONTACT_DEFAULT)

def _save_contact(d: dict):
    import json
    with open(_CONTACT_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)

# ── Palette ────────────────────────────────────────────────────────────────
C = {
    "bg":           "#f1f4f8",
    "header_bg":    "#0d1b2a",
    "header_line":  "#1b2d42",
    "left_bg":      "#fff7f7",
    "left_border":  "#e74c3c",
    "left_title":   "#c0392b",
    "mid_bg":       "#f5fffa",
    "mid_border":   "#2ecc71",
    "mid_title":    "#1a8a48",
    "right_bg":     "#f5f7ff",
    "right_border": "#3498db",
    "right_title":  "#1a5fa8",
    "bot_bg":       "#fffff8",
    "bot_border":   "#f0c030",
    "text":         "#1c2833",
    "text2":        "#5d6d7e",
    "text3":        "#909497",
    "neutral":      "#bdc3c7",
    "btn_add":      "#e67e22",
    "btn_import":   "#2980b9",
    "btn_tmpl":     "#27ae60",
    "btn_clear":    "#e74c3c",
    "btn_ai":       "#8e44ad",
    "btn_text":     "#ffffff",
    "kb_btn":       "#ebedef",
    "kb_border":    "#aab7b8",
    "winner_bg":    "#eaf3fb",
    "winner_fg":    "#1a5fa8",
}

def _gen_palette(n: int) -> list[str]:
    """HSL рангҳои тафовутдор барои n лаҳҷа."""
    import colorsys
    colors = []
    for i in range(n):
        h = i / n
        # Гурӯҳи аввал (11 та) — сераш, дигарон — камтар сер
        s = 0.75 if i < 11 else 0.55
        v = 0.80 if i < 11 else 0.70
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        colors.append(f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}")
    return colors

FT  = ("Segoe UI", 10, "bold")
FN  = ("Segoe UI", 10)
FS  = ("Segoe UI",  9)
FXS = ("Segoe UI",  8)
FH  = ("Segoe UI", 12, "bold")
FT2 = ("Segoe UI", 14, "bold")

# Ҷузъҳои нутқ
POS_LABELS = ["—", "исм", "сифат", "феъл", "зарф", "ҷонишин",
              "нидо", "пешоянд", "пайвандак", "дигар"]

CTRL_KEYCODES = {
    67: "<<Copy>>", 86: "<<Paste>>", 88: "<<Cut>>",
    65: "selectall", 90: "undo",
}

SPECIAL_CHARS = [
    ("ҷ", "Ҷ", "Alt+s", 83),
    ("қ", "Қ", "Alt+w", 87),
    ("ҳ", "Ҳ", "Alt+o", 79),
    ("ғ", "Ғ", "Alt+-", 189),
    ("ӯ", "Ӯ", "Alt+=", 187),
    ("ӣ", "Ӣ", "Alt+i", 73),
]
KEYCODE_MAP = {sc[3]: (sc[0], sc[1]) for sc in SPECIAL_CHARS}

# Клавиатураи тоҷикӣ (tajik_keys.py-дан истифода мешавад)


def _tokenize(text):
    # word-word (пайвандак-реша) ҳамчун як token
    result = []
    for m in re.finditer(r"[\wЀ-ӿ]+(?:-[\wЀ-ӿ]+)*|[^\wЀ-ӿ\n]+|\n", text, re.UNICODE):
        tok = m.group()
        is_word = bool(re.match(r"^[\wЀ-ӿ]+(?:-[\wЀ-ӿ]+)*$", tok, re.UNICODE))
        result.append((tok, is_word))
    return result


class DialectApp(tk.Tk):
    def __init__(self):
        super().__init__()
        db.init_db()
        db.init_users_db()
        self._current_user = None
        self.withdraw()
        # ── Аввал вуруд ──────────────────────────────────────────────────
        self._show_login()
        if not self._current_user:
            self.destroy(); return
        # ── Санҷиши литсензия (танҳо барои user) ─────────────────────────
        if self._current_user.get("role") != "admin":
            if not lic.is_activated():
                self._show_license_dialog()
                if not lic.is_activated():
                    self.destroy(); return
        self.deiconify()
        self.data = db.load_data()
        self._api_key = self._load_api_key()
        self._dialect_colors = {}
        self._tag_counter = 0
        self._setup_colors()
        self.title(f"Барномаи лаҳҷаи тоҷикӣ  —  {self._current_user['username']}")
        self.geometry("1300x740")
        self.minsize(1000, 620)
        self.resizable(True, True)
        self.configure(bg=C["bg"])
        self._build()
        self._setup_global_keyboard()
        self._center()

    def _setup_colors(self):
        keys    = list(self.data["dialects"].keys())
        palette = _gen_palette(max(len(keys), 1))
        for i, dk in enumerate(keys):
            self._dialect_colors[dk] = palette[i]

    def _load_api_key(self):
        if os.path.exists(API_KEY_FILE):
            with open(API_KEY_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        return os.environ.get("ANTHROPIC_API_KEY", "")

    def _save_api_key(self, key):
        with open(API_KEY_FILE, "w", encoding="utf-8") as f:
            f.write(key.strip())

    def _center(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h   = self.winfo_width(), self.winfo_height()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ══════════════════════════════════════════════════════════════════════
    def _build(self):
        self._build_header()
        self._build_body()
        self._build_bottom()

    # ── Сарлавҳа ──────────────────────────────────────────────────────────
    def _build_header(self):
        BG = C["header_bg"]

        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x")
        # Хати аксенти рангин дар поён
        tk.Frame(self, bg="#e74c3c", height=3).pack(fill="x")

        # ── Бренд (чап) ─────────────────────────────────────────────
        brand = tk.Frame(hdr, bg=BG)
        brand.pack(side="left", padx=(18, 0), pady=9)

        tk.Label(brand, text="тҶ", font=("Segoe UI", 22, "bold"),
                 bg=BG, fg="#e74c3c").pack(side="left", padx=(0, 10))

        name_f = tk.Frame(brand, bg=BG)
        name_f.pack(side="left")
        tk.Label(name_f, text="Лаҳҷаҳои Тоҷикистон",
                 font=("Segoe UI", 13, "bold"),
                 bg=BG, fg="#ecf0f1").pack(anchor="w")
        tk.Label(name_f, text="Барномаи таҳлили лаҳҷа",
                 font=("Segoe UI", 8),
                 bg=BG, fg="#7f8c8d").pack(anchor="w")

        # ── Тугмаҳо (рост) ──────────────────────────────────────────
        btn_f = tk.Frame(hdr, bg=BG)
        btn_f.pack(side="right", padx=12, pady=8)

        def _hbtn(text, cmd, col, hov):
            r, g, bv = int(col[1:3],16), int(col[3:5],16), int(col[5:7],16)
            shadow = (f"#{max(0,int(r*.45)):02x}"
                      f"{max(0,int(g*.45)):02x}"
                      f"{max(0,int(bv*.45)):02x}")
            b = tk.Button(btn_f, text=text, command=cmd,
                          font=("Segoe UI", 8, "bold"),
                          bg=col, fg="#ffffff",
                          relief="raised", bd=3,
                          cursor="hand2", padx=11, pady=5,
                          highlightthickness=0,
                          activebackground=hov, activeforeground="#ffffff")
            b.bind("<Enter>",
                   lambda e, _b=b, _h=hov: _b.config(bg=_h))
            b.bind("<Leave>",
                   lambda e, _b=b, _c=col: _b.config(bg=_c, relief="raised"))
            b.bind("<ButtonPress-1>",
                   lambda e, _b=b, _s=shadow: _b.config(relief="sunken", bg=_s))
            b.bind("<ButtonRelease-1>",
                   lambda e, _b=b, _h=hov: _b.config(relief="raised", bg=_h))
            b.pack(side="right", padx=3)

        _hbtn("＋ Калима илова",    self._open_add,                "#e67e22", "#ca6f1e")
        _hbtn("📥 Excel/Word",      self._import_file,             "#2980b9", "#1f618d")
        _hbtn("📋 Шаблон",          self._save_template,           "#27ae60", "#1d8348")
        _hbtn("✕  Тоза",            self._clear,                   "#c0392b", "#a93226")
        _hbtn("🤖 AI Таҳлил",       self._ai_analyze,              "#7d3c98", "#6c3483")
        _hbtn("📊 Омор",            self._show_stats,              "#117a65", "#0e6655")
        _hbtn("📚 Луғатхона",       self._open_linguistic_manager, "#1a5276", "#154360")
        _hbtn("🔑 Парол",          self._change_password,                  "#5d4037", "#4e342e")
        if self._current_user and self._current_user.get("role") == "admin":
            _hbtn("💾 Бекап",       self._backup_db,               "#424949", "#2e3131")
            _hbtn("🔄 Навсозӣ",    lambda: updater.check_and_update(self), "#0e6655", "#0a4f40")
            _hbtn("👥 Корбарон",    self._show_admin_panel,        "#5b2c6f", "#4a235a")
        tk.Frame(self, bg=C["header_line"], height=1).pack(fill="x")

    # ── Асосӣ — 3 сутун ───────────────────────────────────────────────────
    def _build_body(self):
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=8, pady=8)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=4)
        body.columnconfigure(2, weight=3)
        body.rowconfigure(0, weight=1)
        self._build_left(body)
        self._build_mid(body)
        self._build_right(body)

    # ── Сутуни чап ────────────────────────────────────────────────────────
    def _build_left(self, parent):
        outer = tk.Frame(parent, bg=C["left_border"], bd=2, relief="solid")
        outer.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        tk.Label(outer, text="Матни лаҳҷавиро ворид намоед",
                 font=FT, bg=C["left_bg"], fg=C["left_title"],
                 anchor="center", pady=5).pack(fill="x")
        tk.Frame(outer, bg=C["left_border"], height=1).pack(fill="x")

        # Ҳарфҳои махсус
        kb = tk.Frame(outer, bg=C["left_bg"], pady=3)
        kb.pack(fill="x", padx=4)
        tk.Label(kb, text="Ҳарфҳо:", font=FXS,
                 bg=C["left_bg"], fg=C["text3"]).pack(side="left", padx=(2, 4))
        for lo, hk in ((sc[0], sc[2]) for sc in SPECIAL_CHARS):
            cell = tk.Frame(kb, bg=C["left_bg"])
            cell.pack(side="left", padx=1)
            tk.Button(cell, text=lo, font=("Segoe UI", 10, "bold"),
                      bg=C["kb_btn"], fg=C["left_title"],
                      highlightbackground=C["kb_border"],
                      relief="groove", cursor="hand2", width=2, pady=1,
                      command=lambda c=lo: self._insert_char(c)
                      ).pack()
            tk.Label(cell, text=hk, font=("Segoe UI", 6),
                     bg=C["left_bg"], fg=C["text3"]).pack()

        # Майдони матн
        inp_f = tk.Frame(outer, bg=C["left_bg"])
        inp_f.pack(fill="both", expand=True)
        self.inp = tk.Text(inp_f, font=("Segoe UI", 11), bg=C["left_bg"],
                           fg=C["text"], insertbackground=C["left_title"],
                           relief="flat", wrap="word",
                           selectbackground="#ffcccc",
                           padx=8, pady=6)
        self.inp.pack(fill="both", expand=True)
        self.inp.bind("<KeyRelease>", self._on_key)
        self._bind_tajik_keys(self.inp)
        self._bind_edit_keys(self.inp)

        # Тугмаҳои буфер
        cb = tk.Frame(outer, bg=C["left_bg"])
        cb.pack(fill="x", padx=6, pady=(2, 0))
        for ico, cmd in [
            ("📋 Нусха",   lambda: self.inp.event_generate("<<Copy>>")),
            ("📥 Вставит", lambda: self.inp.event_generate("<<Paste>>")),
            ("✂ Бурид",   lambda: self.inp.event_generate("<<Cut>>")),
            ("☰ Ҳама",    lambda: (self.inp.tag_add("sel", "1.0", "end"),
                                    self.inp.mark_set("insert", "end"))),
        ]:
            tk.Button(cb, text=ico, font=FXS,
                      bg=C["left_bg"], fg=C["text2"],
                      relief="flat", cursor="hand2",
                      padx=6, pady=2, command=cmd
                      ).pack(side="left")

        self.char_lbl = tk.Label(outer, text="0 ҳарф",
                                 font=FXS, bg=C["left_bg"],
                                 fg=C["text3"], anchor="e")
        self.char_lbl.pack(fill="x", padx=6, pady=(0, 2))

        # ── Вариантҳои калима (поён) ──────────────────────────────────
        tk.Frame(outer, bg=C["left_border"], height=1).pack(fill="x")
        var_hdr = tk.Frame(outer, bg=C["left_bg"], pady=2)
        var_hdr.pack(fill="x", padx=6)
        self._var_title_l = tk.Label(var_hdr, text="Вариантҳо — калимаро пахш кунед:",
                                     font=FXS, bg=C["left_bg"], fg=C["text3"])
        self._var_title_l.pack(side="left")

        self._var_scroll_f = tk.Frame(outer, bg=C["left_bg"])
        self._var_scroll_f.pack(fill="x", padx=4, pady=(0, 4))

        self._var_canvas = tk.Canvas(self._var_scroll_f, bg=C["left_bg"],
                                     highlightthickness=0, height=85)
        _vsb = ttk.Scrollbar(self._var_scroll_f, orient="horizontal",
                              command=self._var_canvas.xview)
        self._var_canvas.configure(xscrollcommand=_vsb.set)
        _vsb.pack(side="bottom", fill="x")
        self._var_canvas.pack(fill="x")
        self._var_frame = tk.Frame(self._var_canvas, bg=C["left_bg"])
        self._var_win = self._var_canvas.create_window(
            (0, 0), window=self._var_frame, anchor="nw")
        self._var_frame.bind("<Configure>",
            lambda e: self._var_canvas.configure(
                scrollregion=self._var_canvas.bbox("all")))

    # ── Сутуни миёна ──────────────────────────────────────────────────────
    def _build_mid(self, parent):
        outer = tk.Frame(parent, bg=C["mid_border"], bd=2, relief="solid")
        outer.grid(row=0, column=1, sticky="nsew", padx=4)

        tk.Label(outer, text="Матни лаҳҷавӣ (рангин, клик = вариантҳо)",
                 font=FT, bg=C["mid_bg"], fg=C["mid_title"],
                 anchor="center", pady=5).pack(fill="x")
        tk.Frame(outer, bg=C["mid_border"], height=1).pack(fill="x")

        # Легенда рангҳо
        self._leg_frame = tk.Frame(outer, bg=C["mid_bg"])
        self._leg_frame.pack(fill="x", padx=6, pady=(3, 1))

        # Матни рангин
        mid_wrap = tk.Frame(outer, bg=C["mid_bg"])
        mid_wrap.pack(fill="both", expand=True)

        self.mid_text = tk.Text(mid_wrap, font=("Segoe UI", 12),
                                bg=C["mid_bg"], fg=C["text"],
                                relief="flat", wrap="word", state="disabled",
                                padx=10, pady=8, cursor="arrow",
                                selectbackground="#ccffcc",
                                spacing1=3, spacing3=3)
        sb = ttk.Scrollbar(mid_wrap, orient="vertical", command=self.mid_text.yview)
        self.mid_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.mid_text.pack(fill="both", expand=True)
        self.mid_text.tag_configure("nomatch", foreground=C["neutral"],
                                    font=("Segoe UI", 12))

        # Сатри омор: адабӣ | лаҳҷавӣ | ношинохта
        self.word_lbl = tk.Label(outer, text="", font=("Consolas", 8),
                                 bg=C["mid_bg"], fg=C["text3"], anchor="center",
                                 justify="center")
        self.word_lbl.pack(fill="x", padx=6, pady=(2, 1))

        # Сатри морфология: пешванд | реша | пасванд
        self.morph_lbl = tk.Label(outer, text="", font=("Consolas", 8),
                                   bg=C["mid_bg"], fg=C["text3"], anchor="center",
                                   justify="center")
        self.morph_lbl.pack(fill="x", padx=6, pady=(0, 3))

    # ── Сутуни рост ───────────────────────────────────────────────────────
    def _build_right(self, parent):
        outer = tk.Frame(parent, bg=C["right_border"], bd=2, relief="solid")
        outer.grid(row=0, column=2, sticky="nsew", padx=(4, 0))

        tk.Label(outer, text="Тарҷумаи адабӣ",
                 font=FT, bg=C["right_bg"], fg=C["right_title"],
                 anchor="center", pady=5).pack(fill="x")
        tk.Frame(outer, bg=C["right_border"], height=1).pack(fill="x")

        # Натиҷаи асосӣ
        win_f = tk.Frame(outer, bg=C["winner_bg"], pady=5, padx=8)
        win_f.pack(fill="x", padx=4, pady=(4, 2))
        tk.Label(win_f, text="ЛАҲҶАИ МУАЙЯНШУДА",
                 font=("Segoe UI", 7, "bold"),
                 bg=C["winner_bg"], fg=C["text3"]).pack()
        self.winner_name = tk.Label(win_f, text="—",
                                    font=("Segoe UI", 13, "bold"),
                                    bg=C["winner_bg"], fg=C["winner_fg"],
                                    wraplength=200, justify="center")
        self.winner_name.pack(pady=(2, 1))
        self.winner_region = tk.Label(win_f, text="",
                                      font=("Segoe UI", 8),
                                      bg=C["winner_bg"], fg=C["text3"],
                                      wraplength=200, justify="center")
        self.winner_region.pack()
        self.conf_lbl = tk.Label(win_f, text="",
                                 font=("Segoe UI", 9, "bold"),
                                 bg=C["winner_bg"], fg="#aa4400")
        self.conf_lbl.pack(pady=(4, 0))

        tk.Frame(outer, bg=C["right_border"], height=1).pack(fill="x", padx=4, pady=3)

        # Матни адабӣ
        right_wrap = tk.Frame(outer, bg=C["right_bg"])
        right_wrap.pack(fill="both", expand=True)

        self.right_text = tk.Text(right_wrap, font=("Segoe UI", 12),
                                  bg=C["right_bg"], fg=C["text"],
                                  relief="flat", wrap="word", state="disabled",
                                  padx=10, pady=8, cursor="arrow",
                                  selectbackground="#ccccff",
                                  spacing1=3, spacing3=3)
        sb2 = ttk.Scrollbar(right_wrap, orient="vertical",
                             command=self.right_text.yview)
        self.right_text.configure(yscrollcommand=sb2.set)
        sb2.pack(side="right", fill="y")
        self.right_text.pack(fill="both", expand=True)
        self.right_text.tag_configure("nomatch", foreground=C["neutral"],
                                      font=("Segoe UI", 12))

        # ── Вариантҳо (поёни рост) ────────────────────────────────────
        tk.Frame(outer, bg=C["right_border"], height=1).pack(fill="x")
        tk.Label(outer, text="Вариантҳои лаҳҷавӣ:",
                 font=FXS, bg=C["right_bg"], fg=C["text3"],
                 anchor="w", padx=6, pady=2).pack(fill="x")

        self._rvar_scroll_f = tk.Frame(outer, bg=C["right_bg"])
        self._rvar_scroll_f.pack(fill="x", padx=4, pady=(0, 4))

        self._rvar_canvas = tk.Canvas(self._rvar_scroll_f, bg=C["right_bg"],
                                      highlightthickness=0, height=80)
        _rvsb = ttk.Scrollbar(self._rvar_scroll_f, orient="horizontal",
                               command=self._rvar_canvas.xview)
        self._rvar_canvas.configure(xscrollcommand=_rvsb.set)
        _rvsb.pack(side="bottom", fill="x")
        self._rvar_canvas.pack(fill="x")
        self._rvar_frame = tk.Frame(self._rvar_canvas, bg=C["right_bg"])
        self._rvar_canvas.create_window((0, 0), window=self._rvar_frame, anchor="nw")
        self._rvar_frame.bind("<Configure>",
            lambda e: self._rvar_canvas.configure(
                scrollregion=self._rvar_canvas.bbox("all")))

    # ── Поёни зард ────────────────────────────────────────────────────────
    def _build_bottom(self):
        tk.Frame(self, bg=C["bot_border"], height=1).pack(fill="x")
        bot = tk.Frame(self, bg=C["bot_bg"])
        bot.pack(fill="x")

        # Матни таҳлили муфассал
        txt_f = tk.Frame(bot, bg=C["bot_bg"])
        txt_f.pack(side="left", fill="both", expand=True, padx=(10, 4), pady=6)

        self.analysis_text = tk.Text(
            txt_f, font=("Segoe UI", 9),
            bg=C["bot_bg"], fg=C["text2"],
            relief="flat", wrap="word", state="disabled", height=5,
            padx=4, pady=2)
        sb3 = ttk.Scrollbar(txt_f, orient="vertical",
                             command=self.analysis_text.yview)
        self.analysis_text.configure(yscrollcommand=sb3.set)
        sb3.pack(side="right", fill="y")
        self.analysis_text.pack(fill="both", expand=True)

        # Теги барои таҳлил
        self.analysis_text.tag_configure("word_tag",
            font=("Segoe UI", 9, "bold"), foreground=C["text"])
        self.analysis_text.tag_configure("pos_tag",
            font=("Segoe UI", 8, "italic"), foreground="#2060a0")
        self.analysis_text.tag_configure("lit_tag",
            foreground=C["btn_tmpl"])
        self.analysis_text.tag_configure("dialect_tag",
            foreground=C["btn_add"])
        self.analysis_text.tag_configure("region_hdr_tag",
            font=("Segoe UI", 9, "bold"), foreground=C["right_title"])
        self.analysis_text.tag_configure("region_bar_tag",
            font=("Consolas", 8), foreground=C["mid_title"])
        self.analysis_text.tag_configure("sep_tag",
            foreground=C["neutral"])
        self.analysis_text.tag_configure("morph_tag",
            font=("Segoe UI", 8, "italic"), foreground="#5533aa")

        # Тугмаҳои рост
        btn_f = tk.Frame(bot, bg=C["bot_bg"])
        btn_f.pack(side="right", padx=10, pady=6)
        tk.Button(btn_f,
                  text="＋ Илова намудани\nкалимаҳои нав ба база",
                  font=("Segoe UI", 9, "bold"),
                  bg=C["btn_add"], fg=C["btn_text"],
                  relief="flat", cursor="hand2",
                  padx=14, pady=7,
                  command=self._open_add
                  ).pack(pady=(0, 5))
        tk.Button(btn_f,
                  text="✕ Тоза кардани натиҷа",
                  font=("Segoe UI", 9, "bold"),
                  bg=C["btn_clear"], fg=C["btn_text"],
                  relief="flat", cursor="hand2",
                  padx=14, pady=7,
                  command=self._clear
                  ).pack()

    # ══════════════════════════════════════════════════════════════════════
    # Ёрдамчиҳо
    # ══════════════════════════════════════════════════════════════════════
    def _find_literary(self, word, dialects_matched):
        return db.find_literary(word, dialects_matched or None)

    def _find_variants(self, literary_word):
        return db.find_variants(literary_word)

    def _get_pos(self, literary_word):
        return db.get_pos(literary_word)

    def _next_tag(self):
        self._tag_counter += 1
        return f"t{self._tag_counter}"

    def _clear_variants(self):
        for w in self._var_frame.winfo_children():
            w.destroy()
        self._var_title_l.config(text="Вариантҳо — калимаро пахш кунед:")

    def _clear_rvar(self):
        for w in self._rvar_frame.winfo_children():
            w.destroy()

    def _show_word_variants(self, word, dialects_matched):
        self._clear_variants()
        self._clear_rvar()

        # Муайян кун ки калима адабист ё лаҳҷавӣ
        cls = db.classify_word(word)

        if cls["is_literary_only"]:
            # ── Калима адабист: вариантҳои лаҳҷавиашро нишон деҳ ───────
            self._var_title_l.config(
                text=f"«{word}» — адабии стандартӣ ✓  |  вариантҳои лаҳҷавӣ:")
            lit_word = word
        else:
            # ── Калима лаҳҷавист: адабиашро ёб, вариантҳоро нишон деҳ ─
            lit_word = self._find_literary(word, dialects_matched)
            if lit_word.lower() != word.lower():
                self._var_title_l.config(
                    text=f"«{word}» — лаҳҷавӣ  →  адабӣ: «{lit_word}»")
            else:
                self._var_title_l.config(text=f"«{word}» — вариантҳои лаҳҷавӣ:")

        variants = self._find_variants(lit_word)
        if not variants:
            tk.Label(self._var_frame, text="Варианти лаҳҷавӣ ёфт нашуд",
                     font=FXS, bg=C["left_bg"], fg=C["text3"]).pack(padx=4, pady=4)
            return

        for dk, dial_form in variants.items():
            color = self._dialect_colors.get(dk, C["neutral"])
            dname = self.data["dialects"][dk]["name"]
            btn = tk.Button(self._var_frame,
                            text=f"{dial_form}\n{dname}",
                            font=("Segoe UI", 8, "bold"),
                            bg=color, fg="white",
                            relief="flat", cursor="hand2",
                            padx=8, pady=4, wraplength=80, justify="center")
            btn.pack(side="left", padx=3, pady=3)

        for dk, dial_form in variants.items():
            color = self._dialect_colors.get(dk, C["neutral"])
            dname = self.data["dialects"][dk]["name"]
            btn2 = tk.Button(self._rvar_frame,
                             text=f"{dname}\n{dial_form}",
                             font=("Segoe UI", 8, "bold"),
                             bg=color, fg="white",
                             relief="flat", cursor="hand2",
                             padx=8, pady=4, wraplength=80, justify="center")
            btn2.pack(side="left", padx=3, pady=3)

    # ══════════════════════════════════════════════════════════════════════
    # Мантиқ
    # ══════════════════════════════════════════════════════════════════════
    def _on_key(self, _=None):
        text = self.inp.get("1.0", "end").strip()
        self.char_lbl.config(text=f"{len(text)} ҳарф")
        if not text:
            self._reset()
        else:
            self._analyze(text)

    def _analyze(self, text):
        # ── Рангҳои якхела ─────────────────────────────────────────────
        CL  = "#1c2833"   # сиёҳ    — адабӣ
        CR  = "#c0392b"   # сурх    — лаҳҷавӣ (як ноҳия)
        CB  = "#2471a3"   # кабуд   — сермаъно (якчанд ноҳия)
        CO  = "#d35400"   # норинҷӣ — морфологӣ
        CG  = "#1e8449"   # сабз    — ислоҳшуда (дар тарҷума)
        CRU = "#e74c3c"   # сурхи   — дар база нест (дар тарҷума)

        # ── Токенҳо барои SQL ──────────────────────────────────────────
        # Пайвандак-калимаҳоро ба қисматҳо ҷудо мекунем барои луғат
        compound_tokens = re.findall(r"[\wЀ-ӿ]+(?:-[\wЀ-ӿ]+)+", text, re.UNICODE)
        simple_tokens   = re.findall(r"[\wЀ-ӿ]+", text, re.UNICODE)

        scores, word_results = db.detect_dialect(simple_tokens)

        # Морфологии иловагӣ барои нешинохташудаҳо
        unknown_toks = [tok for tok, m, wt in word_results if not m]
        morph_map    = db.morph_classify(unknown_toks)

        # wr_map: tl → (matched, wtype, lit_override)
        wr_map: dict[str, tuple] = {}
        for tok, m, wtype in word_results:
            wr_map.setdefault(tok.lower(), (m, wtype, None))

        for tl, (dks, lit_f, mtype) in morph_map.items():
            wr_map[tl] = (dks, mtype, lit_f)
            if "dialect" in mtype:
                for dk in dks:
                    scores[dk] = scores.get(dk, 0) + 1

        # Пайвандак-калимаҳо: аз қисматҳо ҷамъ мекунем
        for comp in compound_tokens:
            tl = comp.lower()
            if tl in wr_map:
                continue
            parts = comp.split("-")
            all_m: list[str] = []
            wt_best = "unknown"
            lit_best = None
            for p in parts:
                pm, pwt, plit = wr_map.get(p.lower(), ([], "unknown", None))
                for dk in pm:
                    if dk not in all_m:
                        all_m.append(dk)
                if pwt not in ("unknown", "literary_stem") and wt_best == "unknown":
                    wt_best = pwt
                    lit_best = plit
            if all_m:
                wr_map[tl] = (all_m, wt_best or "dialect", lit_best)

        # Ислоҳи кашидашавии садонок (бародарм→бародарам, китобш→китобаш …)
        for tl in list(wr_map.keys()):
            if wr_map[tl][0]:   # аллакай ёфт шудааст — рад кун
                continue
            corrected = db.correct_elision(tl)
            if corrected and corrected != tl:
                wr_map[tl] = ([], "elision_corrected", corrected)

        # Нигоҳ дор барои AI-таҳлил
        self._last_wr_map = wr_map

        total   = max(sum(scores.values()), 1)
        best    = max(scores, key=lambda k: scores[k]) if scores else ""
        best_sc = scores.get(best, 0)
        tokens  = _tokenize(text)

        # ── Миёна: матни рангин ─────────────────────────────────────────
        self.mid_text.configure(state="normal")
        self.mid_text.delete("1.0", "end")
        matched_n = 0

        def _mid_color(wtype, matched):
            if wtype in ("literary", "literary_stem"):
                return CL, ("Segoe UI", 12, "italic"), False   # сиёҳ — адабӣ
            return CR, ("Segoe UI", 12, "bold"), True           # сурх — лаҳҷавӣ

        for tok, is_word in tokens:
            if not is_word:
                self.mid_text.insert("end", tok)
                continue
            matched, wtype, lit_ov = wr_map.get(tok.lower(), ([], "unknown", None))
            if wtype == "elision_corrected":
                # Реша = сиёҳ (адабӣ), пасванди кашидашавӣ = сурх (лаҳҷавӣ)
                matched_n += 1
                _corr = {"м": "ам", "т": "ат", "ш": "аш", "д": "ад"}
                _last = tok[-1].lower() if tok else ""
                if _last in _corr:
                    tag_r = self._next_tag()
                    self.mid_text.tag_configure(tag_r, foreground=CL,
                        font=("Segoe UI", 12, "italic"))
                    self.mid_text.insert("end", tok[:-1], (tag_r,))
                    tag_s = self._next_tag()
                    self.mid_text.tag_configure(tag_s, foreground=CR,
                        font=("Segoe UI", 12, "bold"), underline=True)
                    self.mid_text.insert("end", tok[-1], (tag_s,))
                else:
                    tag = self._next_tag()
                    self.mid_text.tag_configure(tag, foreground=CR,
                        font=("Segoe UI", 12, "bold"), underline=True)
                    self.mid_text.insert("end", tok, (tag,))
            elif matched:
                matched_n += 1
                color, font, uline = _mid_color(wtype, matched)
                # Барои лаҳҷавӣ: пасванди адабии стандартиро ҷудо кун
                _STD = ["ашон", "амон", "атон", "анд", "ям", "ем", "ед",
                        "ам", "ат", "аш", "ро", "ҳо", "он"]
                tl = tok.lower()
                suf = (next((_s for _s in _STD
                             if tl.endswith(_s) and len(tl) > len(_s) + 1), "")
                       if wtype not in ("literary", "literary_stem") else "")
                if suf:
                    # Реша = сурх+ғафс, пасванди стандартӣ = сиёҳ+курсив
                    tag1 = self._next_tag()
                    self.mid_text.tag_configure(tag1, foreground=color,
                        font=font, underline=uline)
                    self.mid_text.insert("end", tok[:-len(suf)], (tag1,))
                    self.mid_text.tag_bind(tag1, "<Button-1>",
                        lambda e, w=tok, dm=matched: self._show_word_variants(w, dm))
                    self.mid_text.tag_bind(tag1, "<Enter>",
                        lambda e: self.mid_text.configure(cursor="hand2"))
                    self.mid_text.tag_bind(tag1, "<Leave>",
                        lambda e: self.mid_text.configure(cursor="arrow"))
                    tag2 = self._next_tag()
                    self.mid_text.tag_configure(tag2, foreground=CL,
                        font=("Segoe UI", 12, "italic"))
                    self.mid_text.insert("end", tok[-len(suf):], (tag2,))
                else:
                    tag = self._next_tag()
                    self.mid_text.tag_configure(tag, foreground=color,
                        font=font, underline=uline)
                    self.mid_text.insert("end", tok, (tag,))
                    self.mid_text.tag_bind(tag, "<Button-1>",
                        lambda e, w=tok, dm=matched: self._show_word_variants(w, dm))
                    self.mid_text.tag_bind(tag, "<Enter>",
                        lambda e: self.mid_text.configure(cursor="hand2"))
                    self.mid_text.tag_bind(tag, "<Leave>",
                        lambda e: self.mid_text.configure(cursor="arrow"))
            else:
                self.mid_text.insert("end", tok, "nomatch")

        self.mid_text.configure(state="disabled")

        # ── Ҳисоби адабӣ / лаҳҷавӣ / ношинохта ────────────────────────
        total_w  = max(len(simple_tokens), 1)
        _LITERARY_TYPES = ("literary", "literary_stem")
        _DIALECT_TYPES  = ("dialect", "both", "dialect_stem",
                           "elision_corrected")   # кашидашавӣ = лаҳҷавӣ

        lit_cnt  = sum(1 for t in simple_tokens
                       if wr_map.get(t.lower(), ([], "unknown", None))[1]
                       in _LITERARY_TYPES)
        dial_cnt = sum(1 for t in simple_tokens
                       if (wr_map.get(t.lower(), ([], "unknown", None))[0]
                           and wr_map.get(t.lower(), ([], "unknown", None))[1]
                           not in _LITERARY_TYPES)
                       or wr_map.get(t.lower(), ([], "unknown", None))[1]
                          in _DIALECT_TYPES)
        unk_cnt  = total_w - lit_cnt - dial_cnt

        lit_pct  = int(lit_cnt  / total_w * 100)
        dial_pct = int(dial_cnt / total_w * 100)
        unk_pct  = 100 - lit_pct - dial_pct

        def _bar(pct, total=20):
            filled = round(pct / 100 * total)
            return "█" * filled + "░" * (total - filled)

        # Сатри 1: адабӣ vs лаҳҷавӣ
        w1 = f"Адабӣ:    {_bar(lit_pct)}  {lit_pct:3d}%  ({lit_cnt} калима)\n"
        w2 = f"Лаҳҷавӣ: {_bar(dial_pct)}  {dial_pct:3d}%  ({dial_cnt} калима)"
        if unk_cnt:
            w2 += f"\nНошинохта:{_bar(unk_pct)}  {unk_pct:3d}%  ({unk_cnt} калима)"
        self.word_lbl.config(text=w1 + w2)

        # ── Таҳлили морфологӣ: пешванд / реша / пасванд ────────────────
        pref_cnt = suf_cnt = root_cnt = morph_total = 0
        morph_cache: dict[str, dict] = {}
        for tl in dict.fromkeys(t.lower() for t in simple_tokens):
            try:
                morph_cache[tl] = db.morph_analyze_word(tl)
            except Exception:
                morph_cache[tl] = {}

        for t in simple_tokens:
            ma  = morph_cache.get(t.lower(), {})
            has_pref = bool(ma.get("prefix", {}).get("form", ""))
            has_suf  = (bool(ma.get("suffix", {}).get("form", "")) or
                        wr_map.get(t.lower(), ([], "unknown", None))[1]
                        == "elision_corrected")
            # Ҳар калима = реша + пешванд? + пасванд?
            m_count = 1 + (1 if has_pref else 0) + (1 if has_suf else 0)
            morph_total += m_count
            root_cnt    += 1
            pref_cnt    += (1 if has_pref else 0)
            suf_cnt     += (1 if has_suf  else 0)

        if morph_total > 0:
            pref_pct = int(pref_cnt / morph_total * 100)
            root_pct = int(root_cnt / morph_total * 100)
            suf_pct  = int(suf_cnt  / morph_total * 100)
            m1 = f"Реша:     {_bar(root_pct)}  {root_pct:3d}%  ({root_cnt} адад)\n"
            m2 = f"Пасванд: {_bar(suf_pct)}  {suf_pct:3d}%  ({suf_cnt} адад)"
            if pref_cnt:
                m2 += f"\nПешванд: {_bar(pref_pct)}  {pref_pct:3d}%  ({pref_cnt} адад)"
            self.morph_lbl.config(text=m1 + m2)
        else:
            self.morph_lbl.config(text="")

        # ── Рост: тарҷумаи адабӣ ───────────────────────────────────────
        self.right_text.configure(state="normal")
        self.right_text.delete("1.0", "end")

        for tok, is_word in tokens:
            if not is_word:
                self.right_text.insert("end", tok)
                continue
            matched, wtype, lit_override = wr_map.get(tok.lower(), ([], "unknown", None))
            tag = self._next_tag()
            if not matched:
                if lit_override and lit_override.lower() != tok.lower():
                    # Кашидашавии садонок ислоҳ шуд (бародарм → бародарам)
                    self.right_text.tag_configure(tag, foreground=CG,
                        font=("Segoe UI", 12, "bold"))
                    self.right_text.insert("end", lit_override, (tag,))
                else:
                    # Дар база нест — адабии стандартӣ ҳисоб мешавад
                    self.right_text.tag_configure(tag, foreground=CL,
                        font=("Segoe UI", 12))
                    self.right_text.insert("end", tok, (tag,))
            elif wtype in ("literary", "literary_stem"):
                # Адабӣ — сиёҳ, бидуни тағйир
                self.right_text.tag_configure(tag, foreground=CL,
                    font=("Segoe UI", 12))
                self.right_text.insert("end", tok, (tag,))
            else:
                # Лаҳҷавӣ → ислоҳ → сабз
                lit = lit_override or self._find_literary(tok, matched)
                self.right_text.tag_configure(tag, foreground=CG,
                    font=("Segoe UI", 12, "bold"))
                self.right_text.insert("end", lit, (tag,))

        self.right_text.configure(state="disabled")

        # ── Легенда рангҳо ──────────────────────────────────────────────
        for w in self._leg_frame.winfo_children():
            w.destroy()
        legend_items = []
        seen_types = set()
        has_lit     = any(wt in ("literary","literary_stem") for _,m,wt,*_ in
                          ((t, *wr_map.get(t.lower(), ([], "unknown", None))) for t, _ in tokens if _))
        has_dialect = any(m and wt not in ("literary","literary_stem") for _,m,wt,*_ in
                          ((t, *wr_map.get(t.lower(), ([], "unknown", None))) for t, _ in tokens if _))
        if has_lit:     legend_items.append((CL, "адабӣ"))
        if has_dialect: legend_items.append((CR, "лаҳҷавӣ"))

        for color, label in legend_items:
            sq = tk.Frame(self._leg_frame, bg=color, width=10, height=10)
            sq.pack(side="left", padx=(4, 1), pady=2)
            sq.pack_propagate(False)
            tk.Label(self._leg_frame, text=label, font=FXS,
                     bg=C["mid_bg"], fg=color).pack(side="left", padx=(0, 8))

        # ── Натиҷаи асосӣ ──────────────────────────────────────────────
        if best_sc == 0:
            self.winner_name.config(text="Лаҳҷа ёфт нашуд", fg=C["text3"])
            self.winner_region.config(text="")
            self.conf_lbl.config(text="Луғатро пур кунед")
        else:
            wd    = self.data["dialects"].get(best, {})
            conf  = int(best_sc / total * 100)
            color = self._dialect_colors.get(best, C["winner_fg"])
            self.winner_name.config(text=wd.get("name", best), fg=color)
            self.winner_region.config(text=wd.get("region", ""))
            self.conf_lbl.config(text=f"Эҳтимол: {conf}%  ·  {best_sc} калима")

        # ── Поён: таҳлили муфассал ─────────────────────────────────────
        self.analysis_text.configure(state="normal")
        self.analysis_text.delete("1.0", "end")

        def _morph_str(tl_key, wtype_key, lit_ov_key):
            ma = morph_cache.get(tl_key, {})
            if not ma:
                return ""
            pref       = ma.get("prefix", {}).get("form", "")
            suf_d      = ma.get("suffix", {})
            suf_form   = suf_d.get("form", "")
            suf_lit    = suf_d.get("literary", "")
            suf_mean   = suf_d.get("meaning", "")
            root_d     = ma.get("root", {})
            root_form  = root_d.get("form", tl_key)
            root_found = root_d.get("found", False)
            root_dial  = root_d.get("is_dialectal", False)
            root_lit   = root_d.get("literary", "")
            # Elision suffix override: morph_analyze_word may not find "м" in DB
            if not suf_form and wtype_key == "elision_corrected" and lit_ov_key:
                _corr = {"м": "ам", "т": "ат", "ш": "аш", "д": "ад"}
                _last = tl_key[-1] if tl_key else ""
                if _last in _corr:
                    suf_form = _last
                    suf_lit  = _corr[_last]
            if not pref and not suf_form and not root_dial:
                return ""
            parts = []
            if pref:
                parts.append(f"пешванд «{pref}-»")
            # Агар root_lit мавҷуд бошад (пешванд дар реша ҷамъ шуд), тамоми реша нишон деҳ
            display_root = (root_lit if root_found and root_lit and root_lit != root_form
                            else root_form)
            if root_dial and root_lit and root_lit != root_form:
                root_str = f"реша «{root_form}» (→ «{root_lit}»)"
            elif not root_found:
                root_str = f"реша «{display_root}» (?)"
            else:
                root_str = f"реша «{display_root}»"
            parts.append(root_str)
            if suf_form:
                suf_s = f"пасванд «-{suf_form}»"
                if suf_lit and suf_lit != suf_form:
                    suf_s += f" (→ «-{suf_lit}»)"
                if suf_mean:
                    suf_s += f" [{suf_mean}]"
                parts.append(suf_s)
            return "   └ морф: " + " + ".join(parts)

        num = 1
        all_toks_lower = {tok.lower() for tok, iw in tokens if iw}
        for tl in sorted(all_toks_lower, key=lambda t: text.lower().find(t)):
            matched, wtype, lit_override = wr_map.get(tl, ([], "unknown", None))
            if not matched and wtype != "elision_corrected":
                continue

            if not matched and wtype == "elision_corrected":
                lit = lit_override or tl
                self.analysis_text.insert("end", f"{num}. ")
                self.analysis_text.insert("end", f"«{tl}»", "word_tag")
                self.analysis_text.insert("end", f" → «{lit}»", "lit_tag")
                self.analysis_text.insert("end", " — кашидашавии садонок\n", "dialect_tag")
                ms = _morph_str(tl, wtype, lit_override)
                if ms:
                    self.analysis_text.insert("end", ms + "\n", "morph_tag")
                num += 1
                continue

            if wtype in ("literary", "literary_stem"):
                pos      = self._get_pos(tl)
                pos_part = f" [{pos}]" if pos and pos != "—" else ""
                morph_s  = " ~морф"   if wtype == "literary_stem" else ""
                self.analysis_text.insert("end", f"{num}. ")
                self.analysis_text.insert("end", f"«{tl}»", "word_tag")
                if pos_part:
                    self.analysis_text.insert("end", pos_part, "pos_tag")
                self.analysis_text.insert("end", " — ", "dialect_tag")
                self.analysis_text.insert("end", f"адабии стандартӣ{morph_s}", "lit_tag")
                variants = self._find_variants(tl)
                if variants:
                    items = list(variants.items())
                    show  = items[:4]
                    dots  = "…" if len(items) > 4 else ""
                    v_str = ", ".join(
                        f"«{df}» ({self.data['dialects'].get(dk, {}).get('name', dk)})"
                        for dk, df in show
                    )
                    self.analysis_text.insert("end", "\n    └ ", "dialect_tag")
                    self.analysis_text.insert("end", f"лаҳҷавӣ: {v_str}{dots}", "lit_tag")
                self.analysis_text.insert("end", "\n")
                ms = _morph_str(tl, wtype, lit_override)
                if ms:
                    self.analysis_text.insert("end", ms + "\n", "morph_tag")
                num += 1
                continue

            lit      = lit_override or self._find_literary(tl, matched)
            pos      = self._get_pos(lit)
            names    = ", ".join(self.data["dialects"][m]["name"]
                                 for m in matched if m in self.data["dialects"])
            lit_part = f" → «{lit}»" if lit.lower() != tl.lower() else ""
            pos_part = f" [{pos}]"   if pos and pos != "—"         else ""
            morph_s  = " ~морф"     if "stem" in wtype             else ""

            self.analysis_text.insert("end", f"{num}. ")
            self.analysis_text.insert("end", f"«{tl}»", "word_tag")
            if pos_part:
                self.analysis_text.insert("end", pos_part, "pos_tag")
            if lit_part:
                self.analysis_text.insert("end", lit_part + morph_s, "lit_tag")
            self.analysis_text.insert("end", " — лаҳҷа: ", "dialect_tag")
            self.analysis_text.insert("end", names + "\n")
            ms = _morph_str(tl, wtype, lit_override)
            if ms:
                self.analysis_text.insert("end", ms + "\n", "morph_tag")
            num += 1

        if num == 1:
            self.analysis_text.insert("end",
                "Калимаҳо дар луғат мавҷуд нестанд. Луғатро пур кунед.")

        # ── Ноҳияҳои истифодабар ──────────────────────────────────────────
        ranked_r = [(k, v) for k, v in
                    sorted(scores.items(), key=lambda x: x[1], reverse=True)
                    if v > 0]
        if ranked_r:
            total_r = max(sum(scores.values()), 1)
            self.analysis_text.insert("end", "\n")
            self.analysis_text.insert("end", "─" * 38 + "\n", "sep_tag")
            self.analysis_text.insert("end",
                "📍 Ноҳияҳое, ки ин лаҳҷаро истифода мебаранд:\n",
                "region_hdr_tag")
            for dk, sc in ranked_r:
                wd   = self.data["dialects"].get(dk, {})
                pct  = int(sc / total_r * 100)
                fill = round(pct / 5)
                bar  = "█" * fill + "░" * (20 - fill)
                name = wd.get("name", dk)
                reg  = wd.get("region", "")
                reg_s = f"  ({reg})" if reg else ""
                self.analysis_text.insert(
                    "end",
                    f"  {name}{reg_s}\n    {bar}  {pct}%  ·  {sc} калима\n",
                    "region_bar_tag")

        self.analysis_text.configure(state="disabled")

    def _reset(self):
        self.mid_text.configure(state="normal")
        self.mid_text.delete("1.0", "end")
        self.mid_text.configure(state="disabled")
        self.word_lbl.config(text="")
        self.morph_lbl.config(text="")
        for w in self._leg_frame.winfo_children():
            w.destroy()

        self.right_text.configure(state="normal")
        self.right_text.delete("1.0", "end")
        self.right_text.configure(state="disabled")
        self.winner_name.config(text="—", fg=C["winner_fg"])
        self.winner_region.config(text="")
        self.conf_lbl.config(text="")

        self._clear_variants()
        self._clear_rvar()
        self.char_lbl.config(text="0 ҳарф")

        self.analysis_text.configure(state="normal")
        self.analysis_text.delete("1.0", "end")
        self.analysis_text.insert("end",
            "Натиҷаи муайян намудани матн ба кадом ноҳия мувофиқат мекунад")
        self.analysis_text.configure(state="disabled")

    def _insert_char(self, ch):
        self.inp.focus_set()
        self.inp.insert(tk.INSERT, ch)
        self._on_key()

    # ══════════════════════════════════════════════════════════════════════
    # Клавиатура
    # ══════════════════════════════════════════════════════════════════════
    def _bind_edit_keys(self, widget):
        is_text = isinstance(widget, tk.Text)

        def on_ctrl(event):
            action = CTRL_KEYCODES.get(event.keycode)
            if not action:
                return
            if action == "selectall":
                if is_text:
                    widget.tag_add("sel", "1.0", "end")
                    widget.mark_set("insert", "end")
                else:
                    widget.select_range(0, "end")
            elif action == "undo":
                try:
                    widget.edit_undo()
                except Exception:
                    pass
            else:
                widget.event_generate(action)
            return "break"

        widget.bind("<Control-KeyPress>", on_ctrl)
        widget.bind("<Button-3>",
                    lambda e: self._show_context_menu(e, widget, is_text))

    def _show_context_menu(self, event, widget, is_text=True):
        m = tk.Menu(widget, tearoff=0, font=FN,
                    bg="white", fg=C["text"],
                    activebackground=C["left_border"],
                    activeforeground="white",
                    bd=1, relief="solid")

        def do_copy():       widget.event_generate("<<Copy>>")
        def do_paste():      widget.event_generate("<<Paste>>")
        def do_cut():        widget.event_generate("<<Cut>>")
        def do_select_all():
            if is_text:
                widget.tag_add("sel", "1.0", "end")
                widget.mark_set("insert", "end")
            else:
                widget.select_range(0, "end")
        def do_undo():
            try: widget.edit_undo()
            except Exception: pass

        m.add_command(label="📋  Нусха гир      Ctrl+C", command=do_copy)
        m.add_command(label="📥  Вставит         Ctrl+V", command=do_paste)
        m.add_command(label="✂   Бурид           Ctrl+X", command=do_cut)
        m.add_separator()
        m.add_command(label="☰   Ҳама интихоб   Ctrl+A", command=do_select_all)
        if is_text:
            m.add_command(label="↩  Бекор кун      Ctrl+Z", command=do_undo)
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    def _bind_tajik_keys(self, widget):
        is_text = isinstance(widget, tk.Text)

        def _insert(w, ch):
            if is_text:
                try: w.delete("sel.first", "sel.last")
                except tk.TclError: pass
                w.insert(tk.INSERT, ch)
            else:
                try: w.delete(w.index("sel.first"), w.index("sel.last"))
                except tk.TclError: pass
                w.insert(w.index(tk.INSERT), ch)
            return "break"

        def on_alt_key(event):
            pair = KEYCODE_MAP.get(event.keycode)
            if pair:
                shifted = bool(event.state & 0x1)
                return _insert(event.widget, pair[1] if shifted else pair[0])

        widget.bind("<Alt-KeyPress>", on_alt_key)
        tajik_keys.apply_tajik_keys(widget)

    def _clear(self):
        self.inp.delete("1.0", "end")
        self._reset()

    # ══════════════════════════════════════════════════════════════════════
    # AI Таҳлил — Claude / Ollama / Офлайн
    # ══════════════════════════════════════════════════════════════════════
    def _ai_analyze(self):
        text = self.inp.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("AI Таҳлил", "Аввал матнро ворид намоед!")
            return
        self._show_ai_window(text)

    # ══════════════════════════════════════════════════════════════════════
    # ВУРУД / БАҚАЙДГИРӢ
    # ══════════════════════════════════════════════════════════════════════
    # ИВАЗ КАРДАНИ ПАРОЛ
    # ══════════════════════════════════════════════════════════════════════
    def _change_password(self):
        if not self._current_user:
            return
        BG  = "#0d1117"
        BG2 = "#161b22"
        FG  = "#e6edf3"
        ACC = "#58a6ff"
        RED = "#f85149"
        GRN = "#3fb950"

        dlg = tk.Toplevel(self)
        dlg.title("🔑 Иваз кардани парол")
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.update_idletasks()
        w, h = 310, 260
        sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
        dlg.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        st = ttk.Style(dlg)
        try: st.theme_use("clam")
        except Exception: pass
        st.configure("CP.TEntry", fieldbackground=BG2, foreground=FG,
                     insertcolor=FG, relief="flat", font=("Segoe UI", 10), padding=4)

        tk.Frame(dlg, bg="#d4ac0d", height=3).pack(fill="x")

        top = tk.Frame(dlg, bg=BG)
        top.pack(fill="x", pady=(12, 6))
        tk.Label(top, text="🔑", font=("Segoe UI", 16),
                 bg=BG, fg="#d4ac0d").pack(side="left", padx=(16, 8))
        lf = tk.Frame(top, bg=BG)
        lf.pack(side="left")
        tk.Label(lf, text="Иваз кардани парол",
                 font=("Segoe UI", 10, "bold"), bg=BG, fg=FG).pack(anchor="w")
        tk.Label(lf, text=f"Корбар: {self._current_user.get('username','')}",
                 font=("Segoe UI", 7), bg=BG, fg="#8b949e").pack(anchor="w")

        tk.Frame(dlg, bg="#21262d", height=1).pack(fill="x", padx=16, pady=(0, 8))

        grid = tk.Frame(dlg, bg=BG)
        grid.pack(fill="x", padx=18)
        grid.columnconfigure(1, weight=1)

        entries = {}
        for i, (lbl, key) in enumerate([
            ("Парол (ҳозира):", "old"),
            ("Парол (нав):",    "new"),
            ("Тасдиқ:",         "conf"),
        ]):
            tk.Label(grid, text=lbl, bg=BG, fg="#8b949e",
                     font=("Segoe UI", 9)).grid(row=i, column=0,
                     sticky="e", padx=(0, 8), pady=3)
            e = ttk.Entry(grid, width=20, style="CP.TEntry", show="•")
            e.grid(row=i, column=1, sticky="ew", pady=3)
            entries[key] = e

        msg = tk.Label(dlg, text="", bg=BG, fg=RED, font=("Segoe UI", 8))
        msg.pack(pady=(4, 2))

        def _save():
            old  = entries["old"].get()
            new  = entries["new"].get()
            conf = entries["conf"].get()
            if not old or not new:
                msg.config(text="⚠  Ҳама майдонҳоро пур кунед"); return
            if len(new) < 4:
                msg.config(text="⚠  Парол ҳадди ақал 4 ҳарф"); return
            if new != conf:
                msg.config(text="⚠  Паролҳои нав мувофиқ нестанд"); return
            ok = db.change_password(self._current_user["id"], old, new)
            if ok:
                msg.config(text="✔  Парол иваз шуд!", fg=GRN)
                dlg.after(800, dlg.destroy)
            else:
                msg.config(text="⚠  Пароли кӯҳна нодуруст")
                entries["old"].delete(0, "end")

        def _btn(parent, text, cmd, bg, hov):
            shd = (f"#{max(0,int(int(bg[1:3],16)*.45)):02x}"
                   f"{max(0,int(int(bg[3:5],16)*.45)):02x}"
                   f"{max(0,int(int(bg[5:7],16)*.45)):02x}")
            b = tk.Button(parent, text=text, command=cmd,
                          font=("Segoe UI", 9, "bold"),
                          bg=bg, fg="#fff", activebackground=hov,
                          activeforeground="#fff",
                          relief="raised", bd=3,
                          cursor="hand2", padx=12, pady=4,
                          highlightthickness=0)
            b.pack(side="left", padx=5)
            b.bind("<Enter>",          lambda e, _b=b: _b.config(bg=hov))
            b.bind("<Leave>",          lambda e, _b=b: _b.config(bg=bg, relief="raised"))
            b.bind("<ButtonPress-1>",  lambda e, _b=b, s=shd: _b.config(relief="sunken", bg=s))
            b.bind("<ButtonRelease-1>",lambda e, _b=b: _b.config(relief="raised", bg=hov))

        bf = tk.Frame(dlg, bg=BG)
        bf.pack(pady=(0, 12))
        _btn(bf, "✔  Захира", _save,       "#1a7a3a", "#22a050")
        _btn(bf, "Бекор",     dlg.destroy, "#424949", "#5a5f5f")

        entries["conf"].bind("<Return>", lambda _: _save())
        entries["new"].bind("<Return>",  lambda _: entries["conf"].focus_set())
        entries["old"].bind("<Return>",  lambda _: entries["new"].focus_set())
        entries["old"].focus_set()

    # ══════════════════════════════════════════════════════════════════════
    # ЛИТСЕНЗИЯ
    # ══════════════════════════════════════════════════════════════════════
    def _show_license_dialog(self):
        BG  = "#0a0d12"
        BG2 = "#131920"
        FG  = "#e6edf3"
        ACC = "#f0c030"
        RED = "#f85149"
        GRN = "#3fb950"

        dlg = tk.Toplevel(self)
        dlg.title("🔐 Фаъолсозии барнома")
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)
        dlg.grab_set()
        dlg.update_idletasks()
        w, h = 400, 280
        sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
        dlg.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        tk.Frame(dlg, bg=ACC, height=3).pack(fill="x")

        tk.Label(dlg, text="🔐", font=("Segoe UI", 28),
                 bg=BG, fg=ACC).pack(pady=(20, 4))
        tk.Label(dlg, text="Лаҳҷаҳои Тоҷикистон",
                 font=("Segoe UI", 13, "bold"), bg=BG, fg=FG).pack()
        tk.Label(dlg, text="Барои истифода калиди литсензияро ворид кунед",
                 font=("Segoe UI", 8), bg=BG, fg="#8b949e").pack(pady=(2, 16))

        tk.Frame(dlg, bg="#21262d", height=1).pack(fill="x", padx=20, pady=(0, 12))

        st = ttk.Style(dlg)
        try: st.theme_use("clam")
        except Exception: pass
        st.configure("Lic.TEntry", fieldbackground=BG2, foreground=FG,
                     insertcolor=FG, relief="flat",
                     font=("Segoe UI", 11), padding=6)

        var = tk.StringVar()
        e = ttk.Entry(dlg, textvariable=var, width=34, style="Lic.TEntry",
                      justify="center")
        e.pack(padx=30)
        tk.Label(dlg, text="Мисол: LAHJA-XXXX-XXXX-XXXX-XXXXXX",
                 font=("Segoe UI", 7), bg=BG, fg="#5d6d7e").pack(pady=(3, 0))

        msg = tk.Label(dlg, text="", bg=BG, fg=RED, font=("Segoe UI", 8))
        msg.pack(pady=(6, 4))

        def _activate():
            key = var.get().strip().upper()
            if lic.activate(key):
                msg.config(text="✔  Барнома фаъол шуд!", fg=GRN)
                dlg.after(700, dlg.destroy)
            else:
                msg.config(text="⚠  Калид нодуруст аст")
                e.focus_set()

        def _contact():
            _c = _load_contact()
            msg.config(
                text=f"Тамос: {_c['phone']}  |  {_c['email']}",
                fg="#e67e22")

        bf = tk.Frame(dlg, bg=BG)
        bf.pack(pady=(0, 8))

        def _lbtn(parent, text, cmd, bg, hov):
            shd = (f"#{max(0,int(int(bg[1:3],16)*.45)):02x}"
                   f"{max(0,int(int(bg[3:5],16)*.45)):02x}"
                   f"{max(0,int(int(bg[5:7],16)*.45)):02x}")
            b = tk.Button(parent, text=text, command=cmd,
                          font=("Segoe UI", 9, "bold"),
                          bg=bg, fg="#fff", activebackground=hov,
                          activeforeground="#fff",
                          relief="raised", bd=3, cursor="hand2",
                          padx=14, pady=5, highlightthickness=0)
            b.pack(side="left", padx=5)
            b.bind("<Enter>",          lambda ev, _b=b: _b.config(bg=hov))
            b.bind("<Leave>",          lambda ev, _b=b: _b.config(bg=bg, relief="raised"))
            b.bind("<ButtonPress-1>",  lambda ev, _b=b, s=shd: _b.config(relief="sunken", bg=s))
            b.bind("<ButtonRelease-1>",lambda ev, _b=b: _b.config(relief="raised", bg=hov))

        _lbtn(bf, "✔  Фаъол кунед", _activate,    "#9a7d0a", "#c9a227")
        _lbtn(bf, "📞  Тамос",       _contact,     "#1a5276", "#1f618d")

        e.bind("<Return>", lambda _: _activate())
        e.focus_set()
        dlg.wait_window()

    # ══════════════════════════════════════════════════════════════════════
    def _show_login(self):
        BG  = "#0d1117"
        BG2 = "#161b22"
        FG  = "#e6edf3"
        ACC = "#58a6ff"
        RED = "#f85149"
        GRN = "#3fb950"

        dlg = tk.Toplevel(self)
        dlg.title("Вуруд")
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.update_idletasks()
        w, h = 300, 230
        sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
        dlg.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)
        dlg.grab_set()
        dlg.focus_force()

        st = ttk.Style(dlg)
        try: st.theme_use("clam")
        except Exception: pass
        st.configure("L.TEntry", fieldbackground=BG2, foreground=FG,
                     insertcolor=FG, relief="flat", font=("Segoe UI", 10), padding=4)

        # ── Акцент хати боло ──────────────────────────────────────────────
        tk.Frame(dlg, bg=ACC, height=3).pack(fill="x")

        # ── Бренд ─────────────────────────────────────────────────────────
        top = tk.Frame(dlg, bg=BG)
        top.pack(fill="x", pady=(12, 8))
        tk.Label(top, text="тҶ", font=("Segoe UI", 18, "bold"),
                 bg=BG, fg="#e74c3c").pack(side="left", padx=(18, 6))
        lf = tk.Frame(top, bg=BG)
        lf.pack(side="left")
        tk.Label(lf, text="Лаҳҷаҳои Тоҷикистон",
                 font=("Segoe UI", 10, "bold"), bg=BG, fg=FG).pack(anchor="w")
        tk.Label(lf, text="Вуруд ба система",
                 font=("Segoe UI", 7), bg=BG, fg="#8b949e").pack(anchor="w")

        tk.Frame(dlg, bg="#21262d", height=1).pack(fill="x", padx=16, pady=(0, 10))

        # ── Майдонҳои воридот ─────────────────────────────────────────────
        grid = tk.Frame(dlg, bg=BG)
        grid.pack(fill="x", padx=18)
        grid.columnconfigure(1, weight=1)

        for row, (lbl, kw) in enumerate([("Логин:", {}), ("Парол:", {"show": "•"})]):
            tk.Label(grid, text=lbl, bg=BG, fg="#8b949e",
                     font=("Segoe UI", 9)).grid(row=row, column=0,
                     sticky="e", padx=(0, 8), pady=4)
            e = ttk.Entry(grid, width=22, style="L.TEntry", **kw)
            e.grid(row=row, column=1, sticky="ew", pady=4)
            if row == 0: e_user = e
            else:        e_pass = e

        msg = tk.Label(dlg, text="", bg=BG, fg=RED, font=("Segoe UI", 8))
        msg.pack(pady=(4, 2))

        # ── Тугмаҳо (3D) ──────────────────────────────────────────────────
        def _btn(parent, text, cmd, bg, hov):
            shd = (f"#{max(0,int(int(bg[1:3],16)*.45)):02x}"
                   f"{max(0,int(int(bg[3:5],16)*.45)):02x}"
                   f"{max(0,int(int(bg[5:7],16)*.45)):02x}")
            b = tk.Button(parent, text=text, command=cmd,
                          font=("Segoe UI", 9, "bold"),
                          bg=bg, fg="#ffffff", activebackground=hov,
                          activeforeground="#ffffff",
                          relief="raised", bd=3,
                          cursor="hand2", padx=12, pady=4,
                          highlightthickness=0)
            b.pack(side="left", padx=5)
            b.bind("<Enter>",          lambda e, _b=b: _b.config(bg=hov))
            b.bind("<Leave>",          lambda e, _b=b: _b.config(bg=bg, relief="raised"))
            b.bind("<ButtonPress-1>",  lambda e, _b=b, s=shd: _b.config(relief="sunken", bg=s))
            b.bind("<ButtonRelease-1>",lambda e, _b=b: _b.config(relief="raised", bg=hov))

        def _login():
            u = e_user.get().strip(); p = e_pass.get()
            if not u or not p:
                msg.config(text="⚠  Логин ва паролро пур кунед"); return
            res = db.verify_user(u, p)
            if res:
                self._current_user = res
                db.log_access(res["id"], "login")
                dlg.destroy()
            else:
                msg.config(text="⚠  Логин ё парол нодуруст")
                e_pass.delete(0, "end")

        def _open_register():
            rdlg = tk.Toplevel(dlg)
            rdlg.title("Бақайдгирӣ")
            rdlg.configure(bg=BG)
            rdlg.resizable(False, False)
            rdlg.grab_set()
            rdlg.update_idletasks()
            rw, rh = 310, 320
            rsw, rsh = rdlg.winfo_screenwidth(), rdlg.winfo_screenheight()
            rdlg.geometry(f"{rw}x{rh}+{(rsw-rw)//2}+{(rsh-rh)//2}")

            tk.Frame(rdlg, bg=GRN, height=3).pack(fill="x")

            top_r = tk.Frame(rdlg, bg=BG)
            top_r.pack(fill="x", pady=(12, 6))
            tk.Label(top_r, text="тҶ", font=("Segoe UI", 18, "bold"),
                     bg=BG, fg="#e74c3c").pack(side="left", padx=(18, 6))
            lf_r = tk.Frame(top_r, bg=BG)
            lf_r.pack(side="left")
            tk.Label(lf_r, text="Бақайдгирӣ",
                     font=("Segoe UI", 10, "bold"), bg=BG, fg=FG).pack(anchor="w")
            tk.Label(lf_r, text="Корбари нав",
                     font=("Segoe UI", 7), bg=BG, fg="#8b949e").pack(anchor="w")

            tk.Frame(rdlg, bg="#21262d", height=1).pack(fill="x", padx=16, pady=(0, 8))

            rg = tk.Frame(rdlg, bg=BG)
            rg.pack(fill="x", padx=18)
            rg.columnconfigure(1, weight=1)

            lbs = ["Логин:", "Парол:", "Тасдиқ:"]
            entries = []
            for i, lb in enumerate(lbs):
                tk.Label(rg, text=lb, bg=BG, fg="#8b949e",
                         font=("Segoe UI", 9)).grid(row=i, column=0,
                         sticky="e", padx=(0, 8), pady=3)
                kw = {"show": "•"} if i > 0 else {}
                e = ttk.Entry(rg, width=20, style="L.TEntry", **kw)
                e.grid(row=i, column=1, sticky="ew", pady=3)
                entries.append(e)
            re_user, re_pass, re_conf = entries

            rmsg = tk.Label(rdlg, text="", bg=BG, fg=RED, font=("Segoe UI", 8))
            rmsg.pack(pady=(4, 2))

            def _do_register():
                u = re_user.get().strip()
                p = re_pass.get()
                c = re_conf.get()
                if not u or not p:
                    rmsg.config(text="⚠  Ҳама майдонҳоро пур кунед"); return
                if len(p) < 4:
                    rmsg.config(text="⚠  Парол ҳадди ақал 4 ҳарф"); return
                if p != c:
                    rmsg.config(text="⚠  Паролҳо мувофиқ нестанд"); return
                res = db.register_user(u, p)
                if res:
                    self._current_user = res
                    db.log_access(res["id"], "login")
                    rmsg.config(text=f"✔  Хуш омадед, {u}!", fg=GRN)
                    rdlg.after(700, lambda: (rdlg.destroy(), dlg.destroy()))
                else:
                    rmsg.config(text="⚠  Ин логин аллакай банд аст")

            rbf = tk.Frame(rdlg, bg=BG)
            rbf.pack(pady=(0, 6))
            _btn(rbf, "✔  Сабт",  _do_register, "#1a7a3a", "#22a050")
            _btn(rbf, "Бекор",    rdlg.destroy,  "#21262d", "#2d333b")

            # ── Муроҷиат ба Админ ─────────────────────────────────────────
            tk.Frame(rdlg, bg="#21262d", height=1).pack(fill="x", padx=16, pady=(6, 0))

            def _show_admin_contact():
                cdlg = tk.Toplevel(rdlg)
                cdlg.title("📞 Муроҷиат ба Админ")
                cdlg.configure(bg=BG)
                cdlg.resizable(False, False)
                cdlg.grab_set()
                cdlg.update_idletasks()
                cw, ch = 320, 210
                csw, csh = cdlg.winfo_screenwidth(), cdlg.winfo_screenheight()
                cdlg.geometry(f"{cw}x{ch}+{(csw-cw)//2}+{(csh-ch)//2}")

                tk.Frame(cdlg, bg="#e67e22", height=3).pack(fill="x")

                tk.Label(cdlg, text="📞  Муроҷиат ба Админ",
                         font=("Segoe UI", 11, "bold"), bg=BG, fg="#e67e22").pack(pady=(14, 4))
                tk.Frame(cdlg, bg="#21262d", height=1).pack(fill="x", padx=16, pady=(0, 10))

                cf = tk.Frame(cdlg, bg=BG)
                cf.pack(fill="x", padx=20)
                cf.columnconfigure(1, weight=1)

                _c = _load_contact()
                ADMIN_INFO = [
                    ("👤 Ном:",   _c["name"]),
                    ("📧 Email:", _c["email"]),
                    ("📱 Тел:",   _c["phone"]),
                ]
                for row, (lbl, val) in enumerate(ADMIN_INFO):
                    tk.Label(cf, text=lbl, bg=BG, fg="#8b949e",
                             font=("Segoe UI", 9)).grid(
                             row=row, column=0, sticky="e", padx=(0, 10), pady=5)
                    tk.Label(cf, text=val, bg=BG, fg=FG,
                             font=("Segoe UI", 9, "bold")).grid(
                             row=row, column=1, sticky="w", pady=5)

                import webbrowser
                def _copy_email():
                    cdlg.clipboard_clear()
                    cdlg.clipboard_append("jeki-102011@mail.ru")
                    copy_btn.config(text="✔  Нусха шуд!")
                    cdlg.after(1500, lambda: copy_btn.config(text="📋  Email нусха"))

                copy_btn = tk.Button(cdlg, text="📋  Email нусха",
                                     command=_copy_email,
                                     font=("Segoe UI", 8, "bold"),
                                     bg="#1a5276", fg="#fff",
                                     activebackground="#1f618d",
                                     relief="raised", bd=2,
                                     cursor="hand2", padx=10, pady=3,
                                     highlightthickness=0)
                copy_btn.pack(pady=(4, 10))

            contact_btn = tk.Button(rdlg,
                text="📞  Бақайдгирӣ мумкин нест? Муроҷиат ба Админ",
                command=_show_admin_contact,
                font=("Segoe UI", 8),
                bg=BG, fg="#e67e22",
                activebackground=BG,
                activeforeground="#d35400",
                relief="flat", bd=0,
                cursor="hand2",
                highlightthickness=0)
            contact_btn.pack(pady=(4, 8))
            contact_btn.bind("<Enter>", lambda e: contact_btn.config(fg="#f39c12",
                             font=("Segoe UI", 8, "underline")))
            contact_btn.bind("<Leave>", lambda e: contact_btn.config(fg="#e67e22",
                             font=("Segoe UI", 8)))

            re_conf.bind("<Return>", lambda _: _do_register())
            re_pass.bind("<Return>", lambda _: re_conf.focus_set())
            re_user.bind("<Return>", lambda _: re_pass.focus_set())
            re_user.focus_set()


        bf = tk.Frame(dlg, bg=BG)
        bf.pack(pady=(0, 8))
        _btn(bf, "➤  Вуруд",       _login,         "#1f6feb", "#388bfd")
        _btn(bf, "＋  Бақайдгирӣ", _open_register, "#21262d", "#2d333b")

        # ── Муроҷиат ба Админ (дар логин ҳам) ────────────────────────────
        tk.Frame(dlg, bg="#21262d", height=1).pack(fill="x", padx=16)

        def _show_admin_contact_login():
            cdlg = tk.Toplevel(dlg)
            cdlg.title("📞 Муроҷиат ба Админ")
            cdlg.configure(bg=BG)
            cdlg.resizable(False, False)
            cdlg.grab_set()
            cdlg.update_idletasks()
            cw, ch = 320, 220
            csw, csh = cdlg.winfo_screenwidth(), cdlg.winfo_screenheight()
            cdlg.geometry(f"{cw}x{ch}+{(csw-cw)//2}+{(csh-ch)//2}")

            tk.Frame(cdlg, bg="#e67e22", height=3).pack(fill="x")
            tk.Label(cdlg, text="📞  Муроҷиат ба Админ",
                     font=("Segoe UI", 11, "bold"),
                     bg=BG, fg="#e67e22").pack(pady=(14, 4))
            tk.Frame(cdlg, bg="#21262d", height=1).pack(fill="x", padx=16, pady=(0, 10))

            cf = tk.Frame(cdlg, bg=BG)
            cf.pack(fill="x", padx=24)
            cf.columnconfigure(1, weight=1)
            _c2 = _load_contact()
            for row, (lbl, val) in enumerate([
                ("👤 Ном:",   _c2["name"]),
                ("📧 Email:", _c2["email"]),
                ("📱 Тел:",   _c2["phone"]),
            ]):
                tk.Label(cf, text=lbl, bg=BG, fg="#8b949e",
                         font=("Segoe UI", 9)).grid(
                         row=row, column=0, sticky="e", padx=(0, 10), pady=5)
                tk.Label(cf, text=val, bg=BG, fg=FG,
                         font=("Segoe UI", 9, "bold")).grid(
                         row=row, column=1, sticky="w", pady=5)

            def _copy():
                cdlg.clipboard_clear()
                cdlg.clipboard_append("jeki-102011@mail.ru")
                cb.config(text="✔  Нусха шуд!")
                cdlg.after(1500, lambda: cb.config(text="📋  Email нусха"))

            cb = tk.Button(cdlg, text="📋  Email нусха", command=_copy,
                           font=("Segoe UI", 8, "bold"),
                           bg="#1a5276", fg="#fff",
                           activebackground="#1f618d",
                           relief="raised", bd=2,
                           cursor="hand2", padx=10, pady=3,
                           highlightthickness=0)
            cb.pack(pady=(4, 12))

        lnk = tk.Button(dlg,
            text="📞  Дастрасӣ нест? Муроҷиат ба Админ",
            command=_show_admin_contact_login,
            font=("Segoe UI", 8),
            bg=BG, fg="#e67e22",
            activebackground=BG, activeforeground="#d35400",
            relief="flat", bd=0, cursor="hand2",
            highlightthickness=0)
        lnk.pack(pady=(5, 10))
        lnk.bind("<Enter>", lambda e: lnk.config(fg="#f39c12",
                 font=("Segoe UI", 8, "underline")))
        lnk.bind("<Leave>", lambda e: lnk.config(fg="#e67e22",
                 font=("Segoe UI", 8)))

        e_pass.bind("<Return>", lambda _: _login())
        e_user.bind("<Return>", lambda _: e_pass.focus_set())
        e_user.focus_set()

        # Баландиро зиёд мекунем
        dlg.geometry(f"300x270+{(dlg.winfo_screenwidth()-300)//2}"
                     f"+{(dlg.winfo_screenheight()-270)//2}")

        dlg.wait_window()

    # ══════════════════════════════════════════════════════════════════════
    # КЛАВИАТУРАИ ТОҶИКӢ — глобалӣ
    # ══════════════════════════════════════════════════════════════════════
    def _setup_global_keyboard(self):
        tajik_keys.setup(self)         # bind_class як бор сабт мешавад
        tajik_keys.walk_and_bind(self) # ҳамаи widget-ҳои мавҷуда

    # ══════════════════════════════════════════════════════════════════════
    # БЕКАП
    # ══════════════════════════════════════════════════════════════════════
    def _backup_db(self):
        import shutil, datetime
        src = db.DB_FILE
        ts  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default = os.path.join(os.path.dirname(src), f"backup_{ts}.db")
        dst = filedialog.asksaveasfilename(
            title="Нусхаи захиравӣ сабт кунед",
            initialfile=f"backup_{ts}.db",
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db"), ("Ҳамаи файлҳо", "*.*")],
        )
        if dst:
            shutil.copy2(src, dst)
            messagebox.showinfo("Бекап", f"✔  Бекап сабт шуд:\n{dst}")
        if self._current_user:
            db.log_access(self._current_user["id"], "backup")

    # ══════════════════════════════════════════════════════════════════════
    # ПАНЕЛИ СУПЕРАДМИН
    # ══════════════════════════════════════════════════════════════════════
    def _show_admin_panel(self):
        BG = "#0d1117"; BG2 = "#161b22"; BG3 = "#21262d"
        FG = "#e6edf3"; ACC = "#58a6ff"; GRN = "#3fb950"
        RED = "#f85149"; FG2 = "#8b949e"; SEL = "#1f6feb"
        BRD = "#30363d"; FN = ("Segoe UI", 10); FT = ("Segoe UI", 10, "bold")

        win = tk.Toplevel(self)
        win.title("👥 Панели суперадмин")
        win.geometry("680x520")
        win.configure(bg=BG)
        win.grab_set()
        win.resizable(True, True)

        st = ttk.Style(win)
        try: st.theme_use("clam")
        except Exception: pass
        st.configure("Adm.Treeview", background=BG2, foreground=FG,
                     fieldbackground=BG2, rowheight=26, font=FN, borderwidth=0)
        st.configure("Adm.Treeview.Heading", background=BG3, foreground=ACC,
                     relief="flat", font=FT)
        st.map("Adm.Treeview", background=[("selected", SEL)],
               foreground=[("selected", FG)])

        # Сарлавҳа
        hf = tk.Frame(win, bg="#1f2937", pady=10)
        hf.pack(fill="x")
        tk.Label(hf, text="👥  Идоракунии корбарон",
                 font=("Segoe UI", 13, "bold"), bg="#1f2937", fg=ACC).pack(side="left", padx=16)

        import datetime

        def _refresh():
            stats = db.get_user_stats()
            # Badges
            for w in badge_frame.winfo_children(): w.destroy()
            for val, lbl, col in [
                (str(stats["total_users"]),  "Корбарон",  ACC),
                (str(stats["total_logins"]), "Вурудҳо",   GRN),
            ]:
                f = tk.Frame(badge_frame, bg=BG3, padx=20, pady=8)
                f.pack(side="left", padx=8, expand=True, fill="x")
                tk.Label(f, text=val, font=("Segoe UI", 22, "bold"), bg=BG3, fg=col).pack()
                tk.Label(f, text=lbl, font=("Segoe UI", 9), bg=BG3, fg=FG2).pack()
            # Ҷадвал
            prev = {tv.item(i, "values")[0]: tv.item(i, "values")
                    for i in tv.get_children()}
            tv.delete(*tv.get_children())
            changed = []
            for i, u in enumerate(stats["users"]):
                logins = next((r["cnt"] for r in stats["per_user"]
                               if r["username"] == u["username"]), 0)
                tag = ("odd",) if i % 2 else ()
                tv.insert("", "end", iid=str(u["id"]),
                          values=(u["username"], u["role"],
                                  u["created_at"] or "—",
                                  u["last_login"]  or "—",
                                  logins),
                          tags=tag)
                old = prev.get(u["username"])
                if old is None:
                    changed.append(f"＋ Нав: {u['username']}")
                elif old[4] != str(logins):
                    changed.append(f"↑ {u['username']}: {old[4]}→{logins} вуруд")
            now = datetime.datetime.now().strftime("%H:%M:%S")
            if changed:
                info_lbl.config(
                    text=f"[{now}]  " + "   ".join(changed),
                    fg=GRN)
            else:
                info_lbl.config(text=f"[{now}]  Тағирот нест", fg=FG2)

        # Badges
        sbf = tk.Frame(win, bg=BG2, padx=16, pady=12)
        sbf.pack(fill="x", padx=12, pady=(10, 6))
        badge_frame = tk.Frame(sbf, bg=BG2)
        badge_frame.pack(fill="x")

        # Хати маълумоти тағирот
        info_lbl = tk.Label(win, text="", bg=BG, fg=FG2,
                            font=("Segoe UI", 8), anchor="w")
        info_lbl.pack(fill="x", padx=16, pady=(0, 2))

        # Тугмачаҳо — аввал pack (поён) то treeview фазояшро гирад
        bf = tk.Frame(win, bg=BG, pady=8)
        bf.pack(side="bottom", fill="x", padx=12)

        # Treeview
        tf = tk.Frame(win, bg=BG)
        tf.pack(fill="both", expand=True, padx=12, pady=(0, 4))
        tf.rowconfigure(0, weight=1); tf.columnconfigure(0, weight=1)

        cols   = ("Логин", "Рол", "Бақайд шуд", "Охирин вуруд", "Вурудҳо")
        widths = (140, 70, 160, 160, 80)
        tv = ttk.Treeview(tf, columns=cols, show="headings",
                          style="Adm.Treeview", height=12)
        for col, w in zip(cols, widths):
            tv.heading(col, text=col, anchor="w")
            tv.column(col, width=w, anchor="w", minwidth=40)
        tv.tag_configure("odd", background="#131920")
        vsb = ttk.Scrollbar(tf, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=vsb.set)
        tv.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        def _delete_user():
            sel = tv.selection()
            if not sel: return
            vals = tv.item(sel[0], "values")
            if vals[0] == "admin":
                messagebox.showwarning("Хато", "Суперадминро ҳазф кардан мумкин нест!", parent=win)
                return
            if messagebox.askyesno("Ҳазф", f"Корбари «{vals[0]}» ҳазф карда шавад?", parent=win):
                conn = db.get_connection()
                conn.execute("DELETE FROM users WHERE id=?", (int(sel[0]),))
                conn.commit(); conn.close()
                _refresh()

        def _sbtn(parent, text, cmd, bg, hov, side="left", px=4):
            shd = (f"#{max(0,int(int(bg[1:3],16)*.45)):02x}"
                   f"{max(0,int(int(bg[3:5],16)*.45)):02x}"
                   f"{max(0,int(int(bg[5:7],16)*.45)):02x}")
            b = tk.Button(parent, text=text, command=cmd,
                          font=("Segoe UI", 9, "bold"),
                          bg=bg, fg="#fff", activebackground=hov,
                          activeforeground="#fff",
                          relief="raised", bd=3, cursor="hand2",
                          padx=10, pady=4, highlightthickness=0)
            b.pack(side=side, padx=px)
            b.bind("<Enter>",          lambda e, _b=b: _b.config(bg=hov))
            b.bind("<Leave>",          lambda e, _b=b: _b.config(bg=bg, relief="raised"))
            b.bind("<ButtonPress-1>",  lambda e, _b=b, s=shd: _b.config(relief="sunken", bg=s))
            b.bind("<ButtonRelease-1>",lambda e, _b=b: _b.config(relief="raised", bg=hov))

        def _edit_contact():
            cdlg = tk.Toplevel(win)
            cdlg.title("📞 Маълумоти тамос")
            cdlg.configure(bg=BG)
            cdlg.resizable(False, False)
            cdlg.grab_set()
            cdlg.update_idletasks()
            cw, ch = 360, 250
            csw = cdlg.winfo_screenwidth(); csh = cdlg.winfo_screenheight()
            cdlg.geometry(f"{cw}x{ch}+{(csw-cw)//2}+{(csh-ch)//2}")

            tk.Frame(cdlg, bg="#e67e22", height=3).pack(fill="x")
            tk.Label(cdlg, text="📞  Маълумоти тамос (Бақайдгирӣ)",
                     font=("Segoe UI", 10, "bold"),
                     bg=BG, fg="#e67e22").pack(pady=(12, 4))
            tk.Frame(cdlg, bg=BG3, height=1).pack(fill="x", padx=16, pady=(0, 8))

            cur = _load_contact()
            fg = tk.Frame(cdlg, bg=BG)
            fg.pack(fill="x", padx=20)
            fg.columnconfigure(1, weight=1)

            st2 = ttk.Style(cdlg)
            try: st2.theme_use("clam")
            except Exception: pass
            st2.configure("CE.TEntry", fieldbackground=BG2, foreground=FG,
                          insertcolor=FG, relief="flat",
                          font=("Segoe UI", 10), padding=4)

            fields = {}
            for i, (lbl, key) in enumerate([
                ("👤 Ном:",   "name"),
                ("📧 Email:", "email"),
                ("📱 Тел:",   "phone"),
            ]):
                tk.Label(fg, text=lbl, bg=BG, fg=FG2,
                         font=("Segoe UI", 9)).grid(
                         row=i, column=0, sticky="e", padx=(0, 8), pady=5)
                e = ttk.Entry(fg, width=26, style="CE.TEntry")
                e.insert(0, cur.get(key, ""))
                e.grid(row=i, column=1, sticky="ew", pady=5)
                fields[key] = e

            cmsg = tk.Label(cdlg, text="", bg=BG, fg=GRN,
                            font=("Segoe UI", 8))
            cmsg.pack(pady=(2, 2))

            def _do_save():
                _save_contact({k: v.get().strip() for k, v in fields.items()})
                cmsg.config(text="✔  Захира шуд!")
                cdlg.after(800, cdlg.destroy)

            cbf = tk.Frame(cdlg, bg=BG)
            cbf.pack(pady=(2, 12))
            _sbtn(cbf, "✔  Захира", _do_save,      "#1a7a3a", "#22a050")
            _sbtn(cbf, "Бекор",     cdlg.destroy,  "#424949", "#5a5f5f")

            list(fields.values())[-1].bind("<Return>", lambda _: _do_save())
            list(fields.values())[0].focus_set()

        _sbtn(bf, "🔄 Навсозӣ",        _refresh,       "#1a3a6e", "#1f4f9e")
        def _gen_key():
            gdlg = tk.Toplevel(win)
            gdlg.title("🔑 Тавлиди калиди литсензия")
            gdlg.configure(bg=BG)
            gdlg.resizable(False, False)
            gdlg.grab_set()
            gdlg.update_idletasks()
            gw, gh = 420, 220
            gsw, gsh = gdlg.winfo_screenwidth(), gdlg.winfo_screenheight()
            gdlg.geometry(f"{gw}x{gh}+{(gsw-gw)//2}+{(gsh-gh)//2}")

            tk.Frame(gdlg, bg="#f0c030", height=3).pack(fill="x")
            tk.Label(gdlg, text="🔑  Тавлиди калиди литсензия",
                     font=("Segoe UI", 11, "bold"),
                     bg=BG, fg="#f0c030").pack(pady=(14, 6))
            tk.Frame(gdlg, bg=BG3, height=1).pack(fill="x", padx=16, pady=(0, 10))

            kvar = tk.StringVar()
            ke = ttk.Entry(gdlg, textvariable=kvar, width=38,
                           font=("Courier New", 11), justify="center",
                           state="readonly")
            ke.pack(padx=20)

            kmsg = tk.Label(gdlg, text="", bg=BG, fg=GRN, font=("Segoe UI", 8))
            kmsg.pack(pady=(4, 4))

            def _new_key():
                k = lic.generate_key()
                kvar.set(k)
                kmsg.config(text="")

            def _copy_key():
                gdlg.clipboard_clear()
                gdlg.clipboard_append(kvar.get())
                kmsg.config(text="✔  Калид нусха шуд!")
                gdlg.after(1500, lambda: kmsg.config(text=""))

            gbf = tk.Frame(gdlg, bg=BG)
            gbf.pack(pady=(4, 14))
            _sbtn(gbf, "🔄 Тавлид",    _new_key,      "#9a7d0a", "#c9a227")
            _sbtn(gbf, "📋 Нусха",     _copy_key,     "#1a5276", "#1f618d")
            _sbtn(gbf, "Пӯшидан",      gdlg.destroy,  "#2e3131", "#3d4040")

            _new_key()

        _sbtn(bf, "✕ Ҳазф",            _delete_user,   "#7a1a1a", "#b02020")
        _sbtn(bf, "📞 Маълумоти тамос", _edit_contact,  "#7a4a1a", "#a06020")
        _sbtn(bf, "🔑 Калиди литсензия",_gen_key,       "#9a7d0a", "#c9a227")
        _sbtn(bf, "Пӯшидан",            win.destroy,    "#2e3131", "#3d4040", side="right")

        _refresh()

    # ══════════════════════════════════════════════════════════════════════
    # Омори база
    # ══════════════════════════════════════════════════════════════════════
    def _show_stats(self):
        from tkinter import ttk, messagebox as mbox

        BG   = "#0d1117"
        BG2  = "#161b22"
        BG3  = "#21262d"
        HDR  = "#0a0f1a"
        ACC  = "#58a6ff"
        ACC2 = "#8b949e"
        GRN  = "#3fb950"
        RED  = "#f85149"
        SEL  = "#1f6feb"
        FN   = ("Segoe UI", 10)
        FT   = ("Segoe UI", 10, "bold")

        REGIONS = [
            ("Вилояти Суғд",           "sugd"),
            ("Вилояти Хатлон",         "khatlon"),
            ("Ноҳияҳои тобеи ҷумҳурӣ", "rrs"),
            ("ВМКБ — Бадахшон",        "vmkb"),
        ]

        win = tk.Toplevel(self)
        win.title("📊 Омори база — Ноҳияҳо")
        win.geometry("800x660")
        win.configure(bg=BG)
        win.resizable(True, True)
        win.grab_set()

        # ── Услуб (ttk) ───────────────────────────────────────────────────
        st = ttk.Style(win)
        try: st.theme_use("clam")
        except Exception: pass
        st.configure("Stats.TEntry",    fieldbackground=BG2, foreground="#e6edf3",
                     insertcolor="#e6edf3", relief="flat", font=FN)
        st.configure("Stats.TCombobox", fieldbackground=BG2, foreground="#e6edf3",
                     selectbackground=SEL, font=FN)
        st.map("Stats.TCombobox",       fieldbackground=[("readonly", BG2)],
                                        foreground=[("readonly", "#e6edf3")])
        st.configure("Stats.Treeview",  background=BG2, foreground="#e6edf3",
                     fieldbackground=BG2, rowheight=28, font=FN, borderwidth=0)
        st.configure("Stats.Treeview.Heading", background="#1c2433",
                     foreground=ACC, relief="flat", font=FT)
        st.map("Stats.Treeview",        background=[("selected", SEL)],
                                        foreground=[("selected", "#ffffff")])

        # ── Ёрдамчии тугмаи 3D ────────────────────────────────────────────
        def _sbtn(parent, text, cmd, bg, fg="#ffffff", hov=None, side="left", px=3):
            if hov is None:
                r, g_, bv = int(bg[1:3],16), int(bg[3:5],16), int(bg[5:7],16)
                hov = (f"#{min(255,int(r*1.2)):02x}"
                       f"{min(255,int(g_*1.2)):02x}"
                       f"{min(255,int(bv*1.2)):02x}")
            r, g_, bv = int(bg[1:3],16), int(bg[3:5],16), int(bg[5:7],16)
            shd = (f"#{max(0,int(r*.45)):02x}"
                   f"{max(0,int(g_*.45)):02x}"
                   f"{max(0,int(bv*.45)):02x}")
            b = tk.Button(parent, text=text, command=cmd,
                          font=("Segoe UI", 9, "bold"),
                          bg=bg, fg=fg, activebackground=hov,
                          activeforeground=fg,
                          relief="raised", bd=3,
                          cursor="hand2", padx=12, pady=5,
                          highlightthickness=0)
            b.pack(side=side, padx=px, pady=4)
            b.bind("<Enter>",        lambda e, _b=b: _b.config(bg=hov))
            b.bind("<Leave>",        lambda e, _b=b: _b.config(bg=bg, relief="raised"))
            b.bind("<ButtonPress-1>",lambda e, _b=b, s=shd: _b.config(relief="sunken", bg=s))
            b.bind("<ButtonRelease-1>",lambda e, _b=b: _b.config(relief="raised", bg=hov))
            return b

        # ── Сарлавҳа ──────────────────────────────────────────────────────
        hf = tk.Frame(win, bg=HDR)
        hf.pack(fill="x")
        inner_hf = tk.Frame(hf, bg=HDR)
        inner_hf.pack(fill="x", padx=16, pady=12)
        tk.Label(inner_hf, text="📊", font=("Segoe UI", 16),
                 bg=HDR, fg=ACC).pack(side="left", padx=(0, 8))
        title_f = tk.Frame(inner_hf, bg=HDR)
        title_f.pack(side="left")
        tk.Label(title_f, text="Омори Базаи Лаҳҷаҳо",
                 font=("Segoe UI", 13, "bold"), bg=HDR, fg="#e6edf3").pack(anchor="w")
        tk.Label(title_f, text="Идоракунии ноҳияҳо ва луғат",
                 font=("Segoe UI", 8), bg=HDR, fg=ACC2).pack(anchor="w")
        tk.Frame(win, bg=ACC, height=2).pack(fill="x")

        # ── Хулоса (карточкаҳо) ───────────────────────────────────────────
        cards_outer = tk.Frame(win, bg=BG, padx=14, pady=10)
        cards_outer.pack(fill="x")

        self._stat_badges_frame = tk.Frame(cards_outer, bg=BG)
        self._stat_badges_frame.pack(fill="x")

        CARD_DEFS = [
            ("Ноҳияҳо",  ACC,  "🗺"),
            ("Калимаҳо", GRN,  "📖"),
            ("Холӣ",     RED,  "⚠"),
            ("Пур",      GRN,  "✅"),
        ]

        def _draw_badges():
            for w in self._stat_badges_frame.winfo_children():
                w.destroy()
            s2    = db.stats()
            dlist = db.get_dialects()
            pd_   = {r["name"]: r["cnt"] for r in s2.get("per_dialect", [])}
            empty = sum(1 for d in dlist if pd_.get(d["name"], 0) == 0)
            vals  = [
                str(len(dlist)),
                f"{s2['total']:,}",
                str(empty),
                str(len(dlist) - empty),
            ]
            for (lbl, col, ico), val in zip(CARD_DEFS, vals):
                outer = tk.Frame(self._stat_badges_frame, bg=BG3,
                                 relief="raised", bd=2)
                outer.pack(side="left", padx=6, expand=True, fill="x")
                inner = tk.Frame(outer, bg=BG3, padx=16, pady=10)
                inner.pack(fill="both", expand=True)
                top_f = tk.Frame(inner, bg=BG3)
                top_f.pack()
                tk.Label(top_f, text=ico, font=("Segoe UI", 14),
                         bg=BG3, fg=col).pack(side="left", padx=(0, 6))
                tk.Label(top_f, text=val, font=("Segoe UI", 22, "bold"),
                         bg=BG3, fg=col).pack(side="left")
                tk.Frame(inner, bg=col, height=2).pack(fill="x", pady=(4, 2))
                tk.Label(inner, text=lbl, font=("Segoe UI", 9),
                         bg=BG3, fg=ACC2).pack()

        _draw_badges()

        # ── Ҷустуҷӯ + фильтр ──────────────────────────────────────────────
        sf_outer = tk.Frame(win, bg=BG2, relief="groove", bd=1)
        sf_outer.pack(fill="x", padx=14, pady=(4, 6))
        sf = tk.Frame(sf_outer, bg=BG2, padx=10, pady=6)
        sf.pack(fill="x")

        tk.Label(sf, text="🔍 Ҷустуҷӯ:", bg=BG2, fg=ACC2,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        q_var = tk.StringVar()
        q_e = ttk.Entry(sf, textvariable=q_var, width=22, style="Stats.TEntry")
        q_e.pack(side="left", padx=(4, 12))

        tk.Label(sf, text="Вилоят:", bg=BG2, fg=ACC2,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        reg_names = ["— Ҳама —"] + [r for r, _ in REGIONS]
        reg_cb = ttk.Combobox(sf, values=reg_names, width=24,
                              state="readonly", style="Stats.TCombobox")
        reg_cb.current(0)
        reg_cb.pack(side="left", padx=(4, 14))

        _sbtn(sf, "＋ Илова", lambda: _open_add(), "#1a7a3a", hov="#22a050")
        _sbtn(sf, "✕ Ҳазф",  lambda: _delete(),   "#7a1a1a", hov="#b02020")

        cnt_lbl = tk.Label(sf, text="", bg=BG2, fg=ACC2,
                           font=("Segoe UI", 9, "bold"))
        cnt_lbl.pack(side="right", padx=8)

        # ── Treeview ──────────────────────────────────────────────────────
        tf = tk.Frame(win, bg=BG)
        tf.pack(fill="both", expand=True, padx=14, pady=(0, 6))

        cols   = ("Калид", "Ном", "Вилоят", "Тартиб", "Калимаҳо")
        widths = (110, 210, 230, 60, 100)
        tv = ttk.Treeview(tf, columns=cols, show="headings",
                          style="Stats.Treeview", height=16)
        for col, w in zip(cols, widths):
            tv.heading(col, text=col, anchor="w")
            tv.column(col, width=w, anchor="w", minwidth=40)
        tv.tag_configure("odd",   background="#131920")
        tv.tag_configure("empty", foreground=RED)
        vsb2 = ttk.Scrollbar(tf, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=vsb2.set)
        tv.grid(row=0, column=0, sticky="nsew")
        vsb2.grid(row=0, column=1, sticky="ns")
        tf.rowconfigure(0, weight=1)
        tf.columnconfigure(0, weight=1)

        def _refresh():
            q   = q_var.get().strip().lower()
            reg = reg_cb.get()
            if reg == "— Ҳама —": reg = ""
            s2    = db.stats()
            pd_   = {r["name"]: r["cnt"] for r in s2.get("per_dialect", [])}
            dlist = db.get_dialects()
            tv.delete(*tv.get_children())
            count = 0
            for i, d in enumerate(dlist):
                if q and q not in d["name"].lower() and q not in d["key"].lower() \
                       and q not in d["region"].lower():
                    continue
                if reg and reg not in d["region"]:
                    continue
                cnt  = pd_.get(d["name"], 0)
                tags = (("odd",) if i % 2 else ()) + (("empty",) if cnt == 0 else ())
                tv.insert("", "end", iid=d["key"],
                          values=(d["key"], d["name"], d["region"],
                                  d.get("sort_order", 0), f"{cnt:,}"),
                          tags=tags)
                count += 1
            cnt_lbl.config(text=f"{count} ноҳия")
            _draw_badges()

        def _open_add():
            dlg = tk.Toplevel(win)
            dlg.title("＋ Ноҳия илова кунед")
            dlg.geometry("380x165")
            dlg.configure(bg=BG)
            dlg.grab_set()
            dlg.resizable(False, False)

            tk.Frame(dlg, bg=ACC, height=3).pack(fill="x")
            tk.Label(dlg, text="＋  Ноҳияи нав илова кунед",
                     font=("Segoe UI", 11, "bold"),
                     bg=BG, fg="#e6edf3").pack(pady=(14, 2))

            grid = tk.Frame(dlg, bg=BG)
            grid.pack(fill="x", padx=20, pady=(6, 4))
            grid.columnconfigure(1, weight=1)

            tk.Label(grid, text="Ном:", bg=BG, fg=ACC2,
                     font=FN).grid(row=0, column=0, sticky="e", padx=(0, 8), pady=6)
            e_nom = ttk.Entry(grid, width=28, style="Stats.TEntry")
            e_nom.grid(row=0, column=1, sticky="ew", pady=6)

            msg = tk.Label(dlg, text="", bg=BG, fg=RED, font=FN)
            msg.pack(pady=(0, 2))

            def _do_save():
                nom = e_nom.get().strip()
                if not nom:
                    msg.config(text="⚠  Ном холӣ!"); return
                key = nom.lower().replace(" ", "_")[:20]
                ok  = db.add_dialect(key, nom, "", 0)
                if not ok:
                    msg.config(text="⚠  Ин ном аллакай мавҷуд аст!"); return
                _refresh()
                dlg.destroy()

            bf = tk.Frame(dlg, bg=BG)
            bf.pack(pady=(0, 12))
            _sbtn(bf, "✔  Захира", _do_save,      "#1a7a3a", hov="#22a050")
            _sbtn(bf, "Бекор",     dlg.destroy,   "#424949", hov="#5a5f5f")

            e_nom.bind("<Return>", lambda _: _do_save())
            e_nom.focus_set()

        def _delete():
            sel = tv.selection()
            if not sel:
                mbox.showwarning("Хато", "Ноҳияро интихоб кунед!", parent=win); return
            vals = tv.item(sel[0], "values")
            name, key, cnt = vals[1], sel[0], vals[4].replace(",", "")
            if mbox.askyesno("Ҳазф",
                    f"Ноҳияи «{name}» ҳазф карда шавад?\n"
                    f"Калимаҳои вобаста ({cnt} дона) низ ҳазф мешаванд.",
                    parent=win):
                db.delete_dialect(key)
                _refresh()

        # Ҷустуҷӯ — зинда
        q_var.trace_add("write", lambda *_: _refresh())
        reg_cb.bind("<<ComboboxSelected>>", lambda _: _refresh())

        _refresh()

    def _open_linguistic_manager(self):
        win = manage_linguistic.open_as_toplevel(self)
        self.after(50, lambda: tajik_keys.walk_and_bind(win))

    def _show_ai_window(self, text):
        BG   = "#1a0a2e"
        BG2  = "#0f0720"
        HDR  = "#2d1060"
        ACC  = "#d0a0ff"
        ACC2 = "#9060cc"

        win = tk.Toplevel(self)
        win.title("🤖 AI Таҳлили лаҳҷа")
        win.geometry("600x540")
        win.configure(bg=BG)
        win.resizable(True, True)
        win.grab_set()

        # ── Сарлавҳа ──────────────────────────────────────────────────
        hdr = tk.Frame(win, bg=HDR, pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🤖  Зеҳни Сунъӣ — Таҳлили Лаҳҷа",
                 font=("Segoe UI", 13, "bold"),
                 bg=HDR, fg=ACC).pack(side="left", padx=16)

        # ── Матни воридшуда ────────────────────────────────────────────
        inp_f = tk.Frame(win, bg=BG, padx=12, pady=4)
        inp_f.pack(fill="x")
        tk.Label(inp_f, text="Матн:", font=("Segoe UI", 8),
                 bg=BG, fg=ACC2).pack(anchor="w")
        tk.Label(inp_f,
                 text=text[:100] + ("…" if len(text) > 100 else ""),
                 font=("Segoe UI", 10, "italic"),
                 bg="#2a1045", fg="#e0c0ff",
                 wraplength=560, justify="left",
                 anchor="w", padx=8, pady=5).pack(fill="x")

        # ── Тугмаҳои интихоби ҳолат ────────────────────────────────────
        mode_f = tk.Frame(win, bg=BG, pady=6)
        mode_f.pack(fill="x", padx=12)

        ollama_ok  = offline_analyzer.is_ollama_running()
        ollama_mdl = offline_analyzer.get_ollama_models() if ollama_ok else []

        MODE_BTNS = {}
        active_mode = tk.StringVar(value="")

        def _set_mode(m):
            active_mode.set(m)
            for k, b in MODE_BTNS.items():
                b.config(bg="#6020a0" if k == m else "#2a1045",
                         relief="flat")

        for key, label, avail in [
            ("claude", "☁ Claude API", bool(self._api_key)),
            ("ollama", f"🏠 Ollama{'  ✓' if ollama_ok else '  ✗'}", True),
            ("stats",  "📊 Офлайн",    True),
        ]:
            b = tk.Button(mode_f, text=label,
                          font=("Segoe UI", 9, "bold"),
                          bg="#2a1045", fg=ACC,
                          activebackground="#6020a0", activeforeground=ACC,
                          relief="flat", cursor="hand2",
                          padx=12, pady=5,
                          command=lambda k=key: _set_mode(k))
            b.pack(side="left", padx=(0, 6))
            MODE_BTNS[key] = b

        # Ollama моделҳо
        olm_f = tk.Frame(win, bg=BG, padx=12)
        olm_f.pack(fill="x")
        tk.Label(olm_f, text="Модели Ollama:", font=("Segoe UI", 8),
                 bg=BG, fg=ACC2).pack(side="left", padx=(0, 6))
        olm_var = tk.StringVar(value=ollama_mdl[0] if ollama_mdl else "")
        olm_cb  = ttk.Combobox(olm_f, values=ollama_mdl, textvariable=olm_var,
                                state="readonly" if ollama_mdl else "disabled",
                                font=("Segoe UI", 9), width=22)
        olm_cb.pack(side="left")
        if not ollama_ok:
            tk.Label(olm_f,
                     text="Насб кунед: https://ollama.com  →  ollama pull gemma3:4b",
                     font=("Segoe UI", 7), bg=BG, fg="#886688"
                     ).pack(side="left", padx=8)

        tk.Frame(win, bg="#6030aa", height=1).pack(fill="x", padx=12, pady=(4, 0))

        # ── Натиҷа ──────────────────────────────────────────────────────
        res_f = tk.Frame(win, bg=BG, padx=12)
        res_f.pack(fill="both", expand=True, pady=(4, 0))

        result_box = tk.Text(res_f, font=("Segoe UI", 10),
                             bg=BG2, fg="#e8d8ff",
                             relief="flat", wrap="word", state="disabled",
                             padx=10, pady=8,
                             insertbackground=ACC,
                             selectbackground="#4020a0")
        sb = ttk.Scrollbar(res_f, orient="vertical", command=result_box.yview)
        result_box.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        result_box.pack(fill="both", expand=True)

        status_lbl = tk.Label(win, text="Ҳолатро интихоб кунед ва тугмаи «Таҳлил»-ро пахш кунед",
                              font=("Segoe UI", 9), bg=BG, fg=ACC2)
        status_lbl.pack(pady=4)

        # ── Тугмаҳои поён ────────────────────────────────────────────────
        bot_f = tk.Frame(win, bg=BG, pady=6)
        bot_f.pack(fill="x")

        done   = [False]
        dots   = ["⏳  Таҳлил…", "⏳  Таҳлил·", "⏳  Таҳлил··", "⏳  Таҳлил···"]
        dot_i  = [0]

        def animate():
            if not done[0]:
                dot_i[0] = (dot_i[0] + 1) % len(dots)
                status_lbl.config(text=dots[dot_i[0]])
                win.after(400, animate)

        def _show(txt):
            done[0] = True
            result_box.configure(state="normal")
            result_box.delete("1.0", "end")
            result_box.insert("end", txt)
            result_box.configure(state="disabled")
            status_lbl.config(text="✔  Тайёр")

        def _err(msg):
            done[0] = True
            result_box.configure(state="normal")
            result_box.delete("1.0", "end")
            result_box.insert("end", f"⚠  {msg}")
            result_box.configure(state="disabled")
            status_lbl.config(text="❌  Хато")

        def _run():
            m = active_mode.get()
            if not m:
                messagebox.showinfo("Интихоб", "Ҳолатро интихоб кунед:\n☁ Claude · 🏠 Ollama · 📊 Офлайн")
                return
            done[0] = False
            animate()
            result_box.configure(state="normal")
            result_box.delete("1.0", "end")
            result_box.insert("end", "")
            result_box.configure(state="disabled")

            # Калимаҳои адабие, ки дар матн ёфт шудаанд
            _wr = getattr(self, "_last_wr_map", {})
            lit_words = sorted({
                tok for tok, val in _wr.items()
                if val[1] in ("literary", "literary_stem") and val[0]
            })

            if m == "claude":
                if not self._api_key:
                    self._open_api_key_dialog(
                        on_success=lambda: (status_lbl.config(text="Такрор мезанем…"),
                                            analyze_dialect(text, self._api_key, _show, _err,
                                                            lit_words=lit_words)))
                    done[0] = True
                    return
                analyze_dialect(text, self._api_key, _show, _err, lit_words=lit_words)

            elif m == "ollama":
                mdl = olm_var.get()
                if not mdl:
                    _err("Модели Ollama интихоб нашудааст.\n"
                         "Оллама кушоед ва модел зеред:\n"
                         "  ollama pull gemma3:4b")
                    return
                offline_analyzer.analyze_ollama(text, mdl, _show, _err, lit_words=lit_words)

            else:  # stats
                result = offline_analyzer.analyze_stats(text, lit_words=lit_words)
                _show(result)

        def _copy():
            txt = result_box.get("1.0", "end").strip()
            if txt:
                win.clipboard_clear()
                win.clipboard_append(txt)

        tk.Button(bot_f, text="▶ Таҳлил", command=_run,
                  font=("Segoe UI", 10, "bold"),
                  bg="#6020a0", fg=ACC,
                  relief="flat", cursor="hand2", padx=16, pady=6
                  ).pack(side="left", padx=12)
        tk.Button(bot_f, text="📋 Нусха", command=_copy,
                  font=("Segoe UI", 9), bg="#2a1045", fg=ACC,
                  relief="flat", cursor="hand2", padx=10, pady=5
                  ).pack(side="left", padx=4)
        tk.Button(bot_f, text="🔑 API калид",
                  command=lambda: self._open_api_key_dialog(),
                  font=("Segoe UI", 9), bg="#2a1045", fg=ACC,
                  relief="flat", cursor="hand2", padx=10, pady=5
                  ).pack(side="left", padx=4)
        tk.Button(bot_f, text="✕ Пӯшидан", command=win.destroy,
                  font=("Segoe UI", 9), bg="#601020", fg="#ffaaaa",
                  relief="flat", cursor="hand2", padx=10, pady=5
                  ).pack(side="right", padx=12)

        # Пешфарз: агар Claude калид дошта бошад → Claude, агар Ollama → Ollama, вагарна Stats
        if self._api_key:
            _set_mode("claude")
        elif ollama_ok and ollama_mdl:
            _set_mode("ollama")
        else:
            _set_mode("stats")

    def _open_api_key_dialog(self, on_success=None):
        win = tk.Toplevel(self)
        win.title("Калиди API")
        win.geometry("460x220")
        win.configure(bg="#1a0a2e")
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="🔑  Калиди Anthropic API",
                 font=("Segoe UI", 12, "bold"),
                 bg="#1a0a2e", fg="#d0a0ff").pack(pady=(18, 4))
        tk.Label(win,
                 text="Калидро аз console.anthropic.com гиред\nва инҷо ворид намоед:",
                 font=("Segoe UI", 9), bg="#1a0a2e", fg="#9060cc",
                 justify="center").pack(pady=4)

        key_var = tk.StringVar(value=self._api_key)
        key_e = tk.Entry(win, textvariable=key_var, font=("Consolas", 10),
                         bg="#0f0720", fg="#e0c0ff",
                         insertbackground="#d0a0ff",
                         show="•", relief="flat", width=44)
        key_e.pack(padx=20, ipady=6)

        show_var = tk.BooleanVar(value=False)
        def toggle_show():
            key_e.config(show="" if show_var.get() else "•")
        tk.Checkbutton(win, text="Нишон деҳ", variable=show_var,
                       command=toggle_show,
                       bg="#1a0a2e", fg="#9060cc",
                       selectcolor="#2d1060",
                       activebackground="#1a0a2e",
                       font=("Segoe UI", 9)).pack(pady=4)

        msg = tk.Label(win, text="", font=("Segoe UI", 9), bg="#1a0a2e")
        msg.pack()

        def save():
            k = key_var.get().strip()
            if not k:
                msg.config(text="⚠  Калид холӣ аст", fg="#ff6060")
                return
            self._api_key = k
            self._save_api_key(k)
            msg.config(text="✔  Захира шуд", fg="#60ff60")
            win.after(800, win.destroy)
            if on_success:
                win.after(900, on_success)

        tk.Button(win, text="✔  Захира кун", command=save,
                  font=("Segoe UI", 10, "bold"),
                  bg="#6020a0", fg="#ffffff",
                  relief="flat", cursor="hand2", padx=16, pady=5
                  ).pack(pady=8)

    # ══════════════════════════════════════════════════════════════════════
    # Илова кардани калима (бо ҷузъи нутқ)
    # ══════════════════════════════════════════════════════════════════════
    def _open_add(self):
        win = tk.Toplevel(self)
        win.title("Илова кардани калима")
        win.geometry("620x640")
        win.configure(bg="#f8f8f8")
        win.resizable(True, True)
        win.grab_set()

        BG = "#f8f8f8"
        dk_keys  = list(self.data["dialects"].keys())
        dk_names = [v["name"] for v in self.data["dialects"].values()]

        tk.Label(win, text="＋  Калима ба луғат илова кунед",
                 font=FH, bg=BG, fg=C["btn_add"]).pack(pady=(10, 4))

        # ── Ноҳияҳо — checkbox-ҳои чандинтаинтихобшаванда ────────────────
        dk_frame_outer = tk.LabelFrame(win, text="Ноҳияҳо (якчанд интихоб кардан мумкин)",
                                       font=FXS, bg=BG, fg=C["text2"],
                                       padx=4, pady=4)
        dk_frame_outer.pack(fill="x", padx=14, pady=(0, 4))

        dkc_wrap = tk.Frame(dk_frame_outer, bg=BG)
        dkc_wrap.pack(fill="x")

        dkc = tk.Canvas(dkc_wrap, bg=BG, highlightthickness=0, height=110)
        dkc_sb = ttk.Scrollbar(dkc_wrap, orient="vertical", command=dkc.yview)
        dkc.configure(yscrollcommand=dkc_sb.set)
        dkc_sb.pack(side="right", fill="y")
        dkc.pack(side="left", fill="both", expand=True)

        dkc_inner = tk.Frame(dkc, bg=BG)
        dkc_win_id = dkc.create_window((0, 0), window=dkc_inner, anchor="nw")
        dkc_inner.bind("<Configure>",
                       lambda e: dkc.configure(scrollregion=dkc.bbox("all")))

        dk_vars: dict[str, tk.BooleanVar] = {}

        def _scroll_dkc(e):
            dkc.yview_scroll(-1 * (e.delta // 120), "units")

        def _bind_scroll_rec(widget):
            widget.bind("<MouseWheel>", _scroll_dkc)
            for child in widget.winfo_children():
                _bind_scroll_rec(child)

        def _rebuild_dkc():
            for w in dkc_inner.winfo_children():
                w.destroy()
            # Нигоҳ дор қайдҳои пешин
            prev = {dk: v.get() for dk, v in dk_vars.items()}
            dk_vars.clear()
            dialects_now = db.get_dialects()
            COLS = 3
            for i, d in enumerate(dialects_now):
                dk, name = d["key"], d["name"]
                var = tk.BooleanVar(value=prev.get(dk, False))
                dk_vars[dk] = var
                color = self._dialect_colors.get(dk, "#888888")
                cb_btn = tk.Checkbutton(
                    dkc_inner, text=name, variable=var,
                    font=FXS, bg=BG,
                    fg=color, selectcolor="#e8eeff",
                    activebackground=BG, activeforeground=color,
                    anchor="w", wraplength=160)
                cb_btn.grid(row=i // COLS, column=i % COLS,
                            sticky="w", padx=(4, 12), pady=1)
            _bind_scroll_rec(dkc_inner)
            dkc.bind("<MouseWheel>", _scroll_dkc)
            dkc.update_idletasks()
            dkc.configure(scrollregion=dkc.bbox("all"))

        _rebuild_dkc()

        # Тугмаҳои идора
        tk.Frame(dk_frame_outer, bg="#d8d8d8", height=1).pack(fill="x", pady=(4, 0))
        sel_f = tk.Frame(dk_frame_outer, bg="#f0f0f8")
        sel_f.pack(fill="x", ipady=4)

        def _styled_btn(parent, text, cmd, bg, fg, hover_bg, side="left", pad=(4, 4)):
            r, g_, bv = int(bg[1:3],16), int(bg[3:5],16), int(bg[5:7],16)
            shadow = (f"#{max(0,int(r*.60)):02x}"
                      f"{max(0,int(g_*.60)):02x}"
                      f"{max(0,int(bv*.60)):02x}")
            b = tk.Button(parent, text=text, command=cmd,
                          font=("Segoe UI", 8, "bold"),
                          bg=bg, fg=fg, activebackground=hover_bg,
                          activeforeground=fg,
                          relief="raised", bd=2,
                          cursor="hand2", padx=10, pady=4,
                          highlightthickness=0)
            b.pack(side=side, padx=pad, pady=3)
            b.bind("<Enter>",
                   lambda e, _b=b: _b.config(bg=hover_bg))
            b.bind("<Leave>",
                   lambda e, _b=b: _b.config(bg=bg, relief="raised"))
            b.bind("<ButtonPress-1>",
                   lambda e, _b=b, _s=shadow: _b.config(relief="sunken", bg=_s))
            b.bind("<ButtonRelease-1>",
                   lambda e, _b=b: _b.config(relief="raised", bg=hover_bg))
            return b

        _styled_btn(sel_f, "☑  Ҳама",
                    lambda: [v.set(True) for v in dk_vars.values()],
                    bg="#dde8ff", fg="#1a4fa0", hover_bg="#c0d4ff", pad=(6, 3))
        _styled_btn(sel_f, "☐  Ягон",
                    lambda: [v.set(False) for v in dk_vars.values()],
                    bg="#f5e8e8", fg="#a01a1a", hover_bg="#f0cccc", pad=(0, 10))

        def _add_dialect_dialog():
            d = tk.Toplevel(win)
            d.title("Ноҳияи нав")
            d.geometry("340x200")
            d.configure(bg=BG)
            d.resizable(False, False)
            d.grab_set()
            fields = {}
            d.geometry("320x160")
            for row_i, (lbl, key, w) in enumerate([
                ("Ном:", "name", 26),
                ("Вилоят:", "region", 26),
            ]):
                tk.Label(d, text=lbl, font=FN, bg=BG, fg=C["text2"],
                         anchor="e", width=10).grid(
                    row=row_i, column=0, sticky="e", padx=(10, 4), pady=6)
                e = tk.Entry(d, font=FN, width=w, relief="groove")
                e.grid(row=row_i, column=1, sticky="ew", padx=(0, 10), pady=6)
                fields[key] = e
                self._bind_tajik_keys(e)
                self._bind_edit_keys(e)
            d.columnconfigure(1, weight=1)
            emsg = tk.Label(d, text="", font=FXS, bg=BG, fg="red")
            emsg.grid(row=2, column=0, columnspan=2)

            def _do_add():
                name = fields["name"].get().strip()
                region = fields["region"].get().strip()
                if not name:
                    emsg.config(text="⚠  Номи ноҳия ҳатмӣ аст")
                    return
                # Калид аз ном худкор месозем
                import unicodedata
                key_val = unicodedata.normalize("NFKD", name.lower())
                key_val = re.sub(r"[^\w]", "_", key_val, flags=re.UNICODE)
                key_val = re.sub(r"_+", "_", key_val).strip("_")[:32]
                ok = db.add_dialect(key_val, name, region)
                if ok:
                    self.data = db.load_data()
                    self._setup_colors()
                    _rebuild_dkc()
                    d.destroy()
                else:
                    emsg.config(text="⚠  Ин ноҳия аллакай мавҷуд аст")

            bf = tk.Frame(d, bg=BG)
            bf.grid(row=4, column=0, columnspan=2, pady=6)
            tk.Button(bf, text="✔ Илова", command=_do_add,
                      font=FN, bg=C["btn_add"], fg="white",
                      relief="flat", cursor="hand2", padx=12, pady=4
                      ).pack(side="left", padx=6)
            tk.Button(bf, text="Бекор", command=d.destroy,
                      font=FN, bg="#e8e0d8", fg=C["text2"],
                      relief="flat", cursor="hand2", padx=12, pady=4
                      ).pack(side="left")
            fields["name"].focus_set()

        def _delete_dialect_dialog():
            checked = [dk for dk, v in dk_vars.items() if v.get()]
            if not checked:
                messagebox.showwarning("Ҳазф",
                    "Аввал ноҳияеро қайд кунед, сипас Ҳазф -ро пахш кунед.",
                    parent=win)
                return
            names = ", ".join(
                f"«{self.data['dialects'].get(dk, {}).get('name', dk)}»"
                for dk in checked)
            if not messagebox.askyesno(
                    "Ҳазф", f"Ноҳияҳои зеринро ҳазф кунем?\n{names}", parent=win):
                return
            for dk in checked:
                db.delete_dialect(dk)
            self.data = db.load_data()
            self._setup_colors()
            _rebuild_dkc()

        _styled_btn(sel_f, "＋  Ноҳия илова", _add_dialect_dialog,
                    bg="#e2f4e2", fg="#1a6e1a", hover_bg="#c6eac6", pad=(0, 4))
        _styled_btn(sel_f, "✕  Ноҳия ҳазф", _delete_dialect_dialog,
                    bg="#fde8e8", fg="#a01a1a", hover_bg="#f9cece", pad=(0, 4))

        kind = tk.StringVar(value="word")
        kf = tk.Frame(win, bg=BG)
        kf.pack(anchor="w", padx=14, pady=(4, 2))
        for lbl_txt, val in [("Калима", "word"), ("Ҷумла", "phrase")]:
            tk.Radiobutton(kf, text=lbl_txt, variable=kind, value=val,
                           bg=BG, font=FN).pack(side="left", padx=6)

        # Ҷузъи нутқ
        pos_f = tk.Frame(win, bg=BG)
        pos_f.pack(anchor="w", padx=14, pady=(0, 6))
        tk.Label(pos_f, text="Ҷузъи нутқ:", font=FN, bg=BG,
                 fg=C["text2"]).pack(side="left", padx=(0, 8))
        pos_var = tk.StringVar(value=POS_LABELS[0])
        pos_cb = ttk.Combobox(pos_f, values=POS_LABELS, textvariable=pos_var,
                               state="readonly", font=FN, width=14)
        pos_cb.pack(side="left")

        # Сарлавҳаи сутунҳо
        hdr = tk.Frame(win, bg="#e8e0d8")
        hdr.pack(fill="x", padx=14)
        tk.Label(hdr, text="  Калимаи адабӣ", font=FT, bg="#e8e0d8",
                 fg=C["text2"], width=20, anchor="w").pack(side="left", padx=(4, 0))
        tk.Label(hdr, text="→", font=FN, bg="#e8e0d8",
                 fg=C["text3"]).pack(side="left", padx=6)
        tk.Label(hdr, text="Лаҳҷавӣ", font=FT, bg="#e8e0d8",
                 fg=C["text2"], anchor="w").pack(side="left", fill="x", expand=True)

        # Ҷадвали скроллшаванда
        frame_c = tk.Frame(win, bg=BG)
        frame_c.pack(fill="both", expand=True, padx=14, pady=(0, 2))

        canvas = tk.Canvas(frame_c, bg=BG, highlightthickness=0)
        sb_c   = ttk.Scrollbar(frame_c, orient="vertical", command=canvas.yview)
        table  = tk.Frame(canvas, bg=BG)
        table.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=table, anchor="nw")
        canvas.configure(yscrollcommand=sb_c.set)
        sb_c.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.bind("<MouseWheel>",
                    lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        rows = []

        def _add_row(lit="", dial="", focus_dial=False):
            rf = tk.Frame(table, bg=BG)
            rf.pack(fill="x", pady=1)

            le = tk.Entry(rf, font=FN, bg="white", fg=C["text"],
                          relief="groove", width=20)
            le.insert(0, lit)
            le.pack(side="left", ipady=4, padx=(0, 4), fill="x", expand=True)
            self._bind_tajik_keys(le)
            self._bind_edit_keys(le)

            tk.Label(rf, text="→", font=FN, bg=BG,
                     fg=C["text3"]).pack(side="left", padx=(0, 4))

            de = tk.Entry(rf, font=FN, bg="white", fg=C["text"],
                          relief="groove", width=20)
            de.insert(0, dial)
            de.pack(side="left", ipady=4, fill="x", expand=True)
            self._bind_tajik_keys(de)
            self._bind_edit_keys(de)

            idx = [len(rows)]

            def _rm(f=rf):
                f.destroy()
                rows[:] = [(l, d, f2) for l, d, f2 in rows if f2 is not f]

            tk.Button(rf, text="✕", font=FXS, width=2,
                      bg="#fde8e8", fg="#cc2222",
                      relief="flat", cursor="hand2",
                      command=_rm).pack(side="left", padx=(4, 0))

            def _tab_from_lit(e, de=de):
                de.focus_set()
                return "break"

            def _tab_from_dial(e, idx=idx):
                i = idx[0]
                if i + 1 < len(rows):
                    rows[i + 1][0].focus_set()
                else:
                    _add_row()
                    win.after(50, lambda: rows[-1][0].focus_set())
                return "break"

            def _enter_dial(e):
                _add_row()
                win.after(50, lambda: rows[-1][0].focus_set())
                return "break"

            le.bind("<Tab>", _tab_from_lit)
            de.bind("<Tab>", _tab_from_dial)
            de.bind("<Return>", _enter_dial)

            rows.append((le, de, rf))
            idx[0] = len(rows) - 1

            if focus_dial:
                win.after(30, de.focus_set)
            else:
                win.after(30, le.focus_set)

            canvas.update_idletasks()
            canvas.yview_moveto(1.0)
            return le, de

        def _paste_from_clip():
            try:
                text = win.clipboard_get()
            except Exception:
                return
            lines = [l for l in text.splitlines() if l.strip()]
            for line in lines:
                line = line.strip()
                if "\t" in line:
                    parts = line.split("\t", 1)
                    _add_row(parts[0].strip(), parts[1].strip())
                elif "=" in line:
                    parts = line.split("=", 1)
                    _add_row(parts[0].strip(), parts[1].strip())
                else:
                    _add_row(line, "", focus_dial=True)

        for _ in range(3):
            _add_row()

        # ── Поёни доимӣ — пеш аз canvas pack мешавад ─────────────────────
        bot = tk.Frame(win, bg="#f0ede8")
        bot.pack(fill="x", side="bottom")
        tk.Frame(bot, bg="#d8cfc4", height=1).pack(fill="x")

        msg = tk.Label(bot, text="", font=FS, bg="#f0ede8", fg="green")
        msg.pack(pady=(4, 0))

        bf = tk.Frame(bot, bg="#f0ede8")
        bf.pack(pady=(4, 6))

        save_btn = tk.Button(bf, text="✔  Илова кун",
                  font=("Segoe UI", 10, "bold"),
                  bg=C["btn_add"], fg="white",
                  activebackground="#8b3a00", activeforeground="white",
                  relief="flat", cursor="hand2", padx=18, pady=7)
        save_btn.pack(side="left", padx=(6, 4))

        clear_btn = tk.Button(bf, text="✕  Тоза кун",
                  font=("Segoe UI", 10),
                  bg="#e8e0d8", fg=C["text2"],
                  activebackground="#d0c8c0", activeforeground=C["text2"],
                  relief="flat", cursor="hand2", padx=14, pady=7)
        clear_btn.pack(side="left", padx=(0, 4))

        close_btn = tk.Button(bf, text="✖  Баромад",
                  font=("Segoe UI", 10),
                  bg="#c0392b", fg="white",
                  activebackground="#922b21", activeforeground="white",
                  relief="flat", cursor="hand2", padx=14, pady=7,
                  command=win.destroy)
        close_btn.pack(side="left", padx=(0, 6))

        # Hover-эффектҳо
        for btn, bg, hov in [
            (save_btn,  C["btn_add"], "#8b3a00"),
            (clear_btn, "#e8e0d8",   "#d0c8c0"),
            (close_btn, "#c0392b",   "#922b21"),
        ]:
            btn.bind("<Enter>", lambda e, b=btn, h=hov: b.config(bg=h))
            btn.bind("<Leave>", lambda e, b=btn, n=bg:  b.config(bg=n))

        # ── Сатри кӯмак ────────────────────────────────────────────────
        mid = tk.Frame(win, bg=BG)
        mid.pack(fill="x", padx=14, pady=(2, 2), side="bottom")
        tk.Button(mid, text="＋ Сатри нав", command=_add_row,
                  font=FXS, bg="#e8f0e8", fg="#2d7a2d",
                  relief="flat", cursor="hand2", padx=10, pady=4
                  ).pack(side="left", padx=(0, 6))
        tk.Button(mid, text="📋 Paste аз буфер", command=_paste_from_clip,
                  font=FXS, bg="#e8eeff", fg=C["btn_import"],
                  relief="flat", cursor="hand2", padx=10, pady=4
                  ).pack(side="left")

        def _save_all():
            selected_dks = [dk for dk, var in dk_vars.items() if var.get()]
            if not selected_dks:
                msg.config(text="⚠  Ҳеч ноҳия интихоб нашудааст", fg="red")
                return
            cat = "phrases" if kind.get() == "phrase" else "words"
            pos = pos_var.get() if pos_var.get() != "—" else ""
            added = updated = 0
            exists_words: list[str] = []

            for le, de, _ in rows:
                lit  = le.get().strip()
                dial = de.get().strip()
                if not lit or not dial:
                    continue
                for dk in selected_dks:
                    status = db.add_word(dk, lit, dial, cat, pos)
                    if status == "added":
                        added += 1
                    elif status == "updated":
                        updated += 1
                    elif status == "unchanged":
                        if lit not in exists_words:
                            exists_words.append(lit)

            parts: list[str] = []
            if added:
                parts.append(f"✔ {added} илова шуд")
            if updated:
                parts.append(f"↻ {updated} навсозӣ шуд")
            if exists_words:
                sample = ", ".join(f"«{w}»" for w in exists_words[:3])
                dots   = "…" if len(exists_words) > 3 else ""
                parts.append(f"ℹ {len(exists_words)} дар база мавҷуд: {sample}{dots}")

            if added or updated:
                self.data = db.load_data()
                for le, de, _ in rows:
                    le.delete(0, "end")
                    de.delete(0, "end")
                if rows:
                    rows[0][0].focus_set()

            if parts:
                color = "green" if added else ("#e67e22" if updated else "#e74c3c")
                msg.config(text="  |  ".join(parts), fg=color)
            elif not (added or updated or exists_words):
                msg.config(text="⚠  Ягон ҷуфт пур нашудааст", fg="red")

        def _clear_all():
            for le, de, _ in rows:
                le.delete(0, "end")
                de.delete(0, "end")
            msg.config(text="")
            if rows:
                rows[0][0].focus_set()

        save_btn.config(command=_save_all)
        clear_btn.config(command=_clear_all)

    # ══════════════════════════════════════════════════════════════════════
    # Импорт
    # ══════════════════════════════════════════════════════════════════════
    def _import_file(self):
        path = filedialog.askopenfilename(
            title="Excel ё Word файл интихоб кунед",
            filetypes=[("Excel", "*.xlsx *.xls"), ("Word", "*.docx"), ("Ҳама", "*.*")])
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        if ext in (".xlsx", ".xls"):
            added, skipped, err = import_excel(path)
        elif ext == ".docx":
            added, skipped, err = import_word(path)
        else:
            messagebox.showerror("Хато", "Танҳо .xlsx ё .docx")
            return
        if err:
            messagebox.showerror("Хато", err)
            return
        self.data = db.load_data()
        self._setup_colors()
        msg = f"✔  {added} калима илова шуд"
        if skipped:
            msg += f"\n⚠  {skipped} сатр холӣ"
        messagebox.showinfo("Тамом", msg)

    def _save_template(self):
        path = filedialog.asksaveasfilename(
            title="Шаблонро захира кунед",
            defaultextension=".xlsx",
            initialfile="lahzha_shablon.xlsx",
            filetypes=[("Excel", "*.xlsx")])
        if not path:
            return
        err = create_template_excel(path)
        if err:
            messagebox.showerror("Хато", err)
        else:
            messagebox.showinfo("Шаблон тайёр",
                f"✔  Захира шуд:\n{path}\n\n"
                "1. Дар Excel кушоед\n2. Калимаҳо нависед\n"
                "3. Захира кунед\n4. 📥 Excel/Word юкл → интихоб кунед")
            os.startfile(os.path.dirname(path))


if __name__ == "__main__":
    app = DialectApp()
    app.mainloop()
