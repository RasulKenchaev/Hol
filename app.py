import sys, io

# Windows: stdout/stderr-ро ба UTF-8 мегузорем то кириллика дуруст кор кунад
if sys.platform == "win32":
    for _s in ("stdout", "stderr"):
        _st = getattr(sys, _s, None)
        if _st and hasattr(_st, "buffer"):
            setattr(sys, _s,
                    io.TextIOWrapper(_st.buffer, encoding="utf-8", errors="replace"))

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os, re
import db
from importer import import_excel, import_word, create_template_excel


def _apply_case(original: str, replacement: str) -> str:
    """Ҳарфи калони аввали оригиналро ба ивазкунак мегузорад."""
    if not original or not replacement:
        return replacement
    if original.isupper():
        return replacement.upper()
    if original[0].isupper():
        return replacement[0].upper() + replacement[1:]
    return replacement
from ai_analyzer import analyze_dialect
import offline_analyzer
import manage_linguistic
import tajik_keys
import updater
import license as lic
from paths import app_dir

API_KEY_FILE    = os.path.join(app_dir(), ".api_key")
_CONTACT_FILE   = os.path.join(app_dir(), ".admin_contact")
_CONTACT_DEFAULT = {
    "name":  "Холмуродов Раҷабали",
    "email": "rajabaliit1995@mail.com",
    "phone": "+992 985111995",
    "photo": "",
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

        # ── Тугмаи "Дигар амалҳо" (чап) ─────────────────────────────
        left_btn_f = tk.Frame(hdr, bg=BG)
        left_btn_f.pack(side="left", padx=12, pady=8)

        _extra_menu = tk.Menu(self, tearoff=0,
                              bg="#1c2833", fg="#ecf0f1",
                              activebackground="#2c3e50",
                              activeforeground="#ecf0f1",
                              font=("Segoe UI", 9, "bold"),
                              relief="flat", bd=0)
        _extra_menu.add_command(label="🤖 AI Таҳлил",
                                command=self._ai_analyze)
        if self._current_user and self._current_user.get("role") == "admin":
            _extra_menu.add_separator()
            _extra_menu.add_command(label="💾 Бекап",
                                    command=self._backup_db)
            _extra_menu.add_command(label="👥 Корбарон",
                                    command=self._show_admin_panel)
            _extra_menu.add_command(label="🔄 Навсозӣ",
                                    command=lambda: updater.check_and_update(self))

        _extra_btn = tk.Button(left_btn_f, text="⋯ Дигар амалҳо",
                               font=("Segoe UI", 8, "bold"),
                               bg="#2c3e50", fg="#ecf0f1",
                               relief="raised", bd=3,
                               cursor="hand2", padx=11, pady=5,
                               highlightthickness=0,
                               activebackground="#3d5166",
                               activeforeground="#ecf0f1")

        def _show_extra(e=None):
            try:
                bx = _extra_btn.winfo_rootx()
                by = _extra_btn.winfo_rooty() + _extra_btn.winfo_height()
                _extra_menu.tk_popup(bx, by)
            finally:
                _extra_menu.grab_release()

        _extra_btn.config(command=_show_extra)
        _extra_btn.bind("<Enter>",  lambda e: _extra_btn.config(bg="#3d5166"))
        _extra_btn.bind("<Leave>",  lambda e: _extra_btn.config(bg="#2c3e50", relief="raised"))
        _extra_btn.bind("<ButtonPress-1>",   lambda e: _extra_btn.config(relief="sunken"))
        _extra_btn.bind("<ButtonRelease-1>", lambda e: _extra_btn.config(relief="raised"))
        _extra_btn.pack(side="left")

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
        _hbtn("📊 Омор",            self._show_stats,              "#117a65", "#0e6655")
        _hbtn("📚 Базаи луғатҳо",    self._open_linguistic_manager, "#1a5276", "#154360")
        _hbtn("🔑 Парол",          self._change_password,                  "#5d4037", "#4e342e")
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

        lhdr = tk.Frame(outer, bg=C["left_bg"])
        lhdr.pack(fill="x")
        tk.Label(lhdr, text="Матни лаҳҷавиро ворид намоед",
                 font=FT, bg=C["left_bg"], fg=C["left_title"],
                 anchor="center", pady=5).pack(fill="x")
        tk.Frame(outer, bg=C["left_border"], height=1).pack(fill="x")


        # Майдони матн
        inp_f = tk.Frame(outer, bg=C["left_bg"])
        inp_f.pack(fill="both", expand=True)

        # Полоси пешниҳоди chips (поён аз равзанаи 1, монанди равзанаи 3)
        self._typing_inp_strip, self._typing_inp_cv, self._typing_inp_inner = \
            self._make_chip_strip(inp_f, C["left_bg"], side="bottom")

        self.inp = tk.Text(inp_f, font=("Segoe UI", 11), bg=C["left_bg"],
                           fg=C["text"], insertbackground=C["left_title"],
                           relief="flat", wrap="word",
                           selectbackground="#ffcccc",
                           padx=8, pady=6)
        self.inp.pack(fill="both", expand=True)
        self.inp.bind("<KeyRelease>", self._on_key)
        self.inp.bind("<ButtonRelease-1>", self._inp_click)
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

        self._mic_recording = False
        self._mic_anim_id   = None
        self._mic_anim_step = 0

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

        tk.Label(outer, text="Матни лаҳҷавӣ",
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

        # ── Боло: сарлавҳа + тугмаи садо ────────────────────────────
        hdr_row = tk.Frame(outer, bg=C["right_bg"])
        hdr_row.pack(side="top", fill="x")
        tk.Label(hdr_row, text="Тарҷумаи адабӣ",
                 font=FT, bg=C["right_bg"], fg=C["right_title"],
                 anchor="center", pady=5).pack(side="left", expand=True)
        self._tts_active = False

        # ── Тугмаҳои садо ва микрофон ──────────────────────────────────
        btn_frame = tk.Frame(hdr_row, bg=C["right_bg"])
        btn_frame.pack(side="right", padx=6)

        def _make_icon_btn(parent, text, cmd, base_bg, hover_bg):
            btn = tk.Button(parent, text=text, command=cmd,
                            bg=base_bg, fg="#ffffff",
                            activebackground=hover_bg, activeforeground="#ffffff",
                            relief="flat", cursor="hand2",
                            font=("Segoe UI Emoji", 12), bd=0,
                            padx=8, pady=3)
            btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg))
            btn.bind("<Leave>", lambda e: btn.config(bg=base_bg))
            return btn

        self._mic_btn = _make_icon_btn(btn_frame, "🎤",
                                       self._start_voice_input,
                                       "#3498db", "#2475a8")
        self._mic_btn.pack(side="left", padx=(0, 4))

        self._tts_btn = _make_icon_btn(btn_frame, "🔊",
                                       self._speak_right,
                                       "#5dade2", "#2e86c1")
        self._tts_btn.pack(side="left")
        tk.Frame(outer, bg=C["right_border"], height=1).pack(side="top", fill="x")

        win_f = tk.Frame(outer, bg=C["winner_bg"], pady=5, padx=8)
        win_f.pack(side="top", fill="x", padx=4, pady=(4, 2))
        tk.Label(win_f,
                 text="КАЛИМАҲОИ ЭҲТИМОЛӢ · БАРХУРД ВА МАНСУБИЯТИ КАЛИМАҲО БА НОҲИЯҲО",
                 font=("Segoe UI", 7, "bold"),
                 bg=C["winner_bg"], fg=C["text3"],
                 wraplength=220, justify="center").pack()
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
        tk.Frame(outer, bg=C["right_border"], height=1).pack(
            side="top", fill="x", padx=4, pady=3)

        # ── Омори тарҷума ────────────────────────────────────────────────
        ST_BG = "#eafaf1"
        stats_f = tk.Frame(outer, bg=ST_BG)
        stats_f.pack(side="top", fill="x", padx=4, pady=(0, 3))
        self._stats_lbl = tk.Label(
            stats_f, text="",
            font=("Segoe UI", 8), bg=ST_BG, fg="#1e8449",
            justify="left", anchor="w", padx=8, pady=2)
        self._stats_lbl.pack(fill="x")
        self._unknown_lbl = tk.Label(
            stats_f, text="",
            font=("Segoe UI", 8), bg=ST_BG, fg="#c0392b",
            justify="left", anchor="w", padx=8,
            wraplength=220)
        self._unknown_lbl.pack(fill="x", pady=(0, 4))
        tk.Frame(outer, bg=C["right_border"], height=1).pack(
            side="top", fill="x", padx=4, pady=(0, 3))

        # ── Поён: AI пешниҳод (аввал поёнро ҷойгир мекунем) ────────────
        AI_BG = "#eef2ff"
        AI_BD = "#3b5bdb"

        ai_outer = tk.Frame(outer, bg=AI_BG)
        ai_outer.pack(side="bottom", fill="x")
        tk.Frame(ai_outer, bg=AI_BD, height=1).pack(side="top", fill="x")
        ai_hdr = tk.Frame(ai_outer, bg=AI_BG)
        ai_hdr.pack(side="top", fill="x")
        tk.Label(ai_hdr, text="🤖 Пешниҳодҳои зеҳни сунъӣ",
                 font=("Segoe UI", 8, "bold"), bg=AI_BG, fg="#1a3a8f",
                 anchor="w", padx=6, pady=3).pack(side="left")
        self._ai_spin_lbl = tk.Label(ai_hdr, text="",
                                     font=("Segoe UI", 8),
                                     bg=AI_BG, fg=C["text3"])
        self._ai_spin_lbl.pack(side="right", padx=6)
        ai_wrap = tk.Frame(ai_outer, bg=AI_BG)
        ai_wrap.pack(side="top", fill="both")
        self._ai_sugg_text = tk.Text(
            ai_wrap, font=("Segoe UI", 10),
            bg=AI_BG, fg=C["text"],
            relief="flat", wrap="word", state="disabled",
            padx=8, pady=4, height=5, cursor="arrow")
        ai_sb = ttk.Scrollbar(ai_wrap, orient="vertical",
                               command=self._ai_sugg_text.yview)
        self._ai_sugg_text.configure(yscrollcommand=ai_sb.set)
        ai_sb.pack(side="right", fill="y")
        self._ai_sugg_text.pack(side="left", fill="both", expand=True)

        # _rvar_frame — пинҳон, танҳо барои мутобиқати боқии код нигоҳ дошта шудааст
        self._rvar_frame = tk.Frame(self)

        # ── Миёна: матни тарҷума (фазои боқимондаро мегирад) ────────────
        right_wrap = tk.Frame(outer, bg=C["right_bg"])
        right_wrap.pack(side="top", fill="both", expand=True)

        # Полоси пешниҳоди калимаҳои ҳарфдор (поён аз матни тарҷума)
        self._typing_right_strip, self._typing_right_cv, self._typing_right_inner = \
            self._make_chip_strip(right_wrap, C["right_bg"], side="bottom")

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
        self.right_text.bind("<ButtonRelease-1>", self._right_click)
        self.right_text.bind("<Button-3>",        self._right_click_poly)
        self.right_text.tag_configure("nomatch", foreground=C["neutral"],
                                      font=("Segoe UI", 12))
        self.right_text.tag_configure("poly_mark",
            underline=True, foreground="#c0392b",
            font=("Segoe UI", 12, "bold"))

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
            self._clear_typing_ac()
        else:
            self._analyze(text)
            self._update_typing_ac()

    def _update_typing_ac(self):
        """Калимаи нопурраро аз курсор гирифта, дар панели 'Вариантҳо' (зери равзанаи 1) нишон медиҳад."""
        import re as _re
        try:
            cursor = self.inp.index(tk.INSERT)
            line_no, col = cursor.split(".")
            line = self.inp.get(f"{line_no}.0", f"{line_no}.{col}")
            i = len(line)
            while i > 0 and line[i - 1].isalpha():
                i -= 1
            last_word = line[i:]
            ws = f"{line_no}.{i}"
            we = f"{line_no}.{col}"
        except Exception:
            last_word, ws, we = "", "1.0", "1.0"

        if len(last_word) < 2:
            self._clear_typing_ac()
            return

        rows = db.search_autocomplete_all(last_word, limit=14)
        if not rows:
            self._clear_typing_ac()
            return

        # Мавқеи калимаи нопурраро барои _ac1_click нигоҳ мекунем
        self._ac_source_w1 = (ws, we)

        expanded: list[dict] = []
        seen: set[str] = set()
        for r in rows:
            for form in (r.get("dialect_form", "").strip(), r.get("literary", "").strip()):
                if form and form not in seen and not _re.search(r"[a-zA-Z]", form):
                    seen.add(form)
                    expanded.append({**r, "_label": form})

        self._show_ac_strip(
            self._typing_inp_strip, self._typing_inp_cv, self._typing_inp_inner,
            expanded, lambda r: self._ac1_click(r))

    def _clear_typing_ac(self):
        """Полосҳои chips-и равзанаи 1 ва 3-ро тоза мекунад."""
        if hasattr(self, "_typing_inp_strip"):
            self._show_ac_strip(
                self._typing_inp_strip, self._typing_inp_cv, self._typing_inp_inner, [], None)
        if hasattr(self, "_typing_right_strip"):
            self._show_ac_strip(
                self._typing_right_strip, self._typing_right_cv,
                self._typing_right_inner, [], None)

    def _analyze(self, text):
        # ── Рангҳои якхела ─────────────────────────────────────────────
        CL  = "#1c2833"   # сиёҳ    — адабӣ
        CR  = "#c0392b"   # сурх    — лаҳҷавӣ (як ноҳия)
        CB  = "#2471a3"   # кабуд   — сермаъно (якчанд ноҳия)
        CO  = "#d35400"   # норинҷӣ — морфологӣ
        CG  = "#1e8449"   # сабз    — ислоҳшуда (дар тарҷума)
        CRU = "#e74c3c"   # сурхи   — дар база нест (дар тарҷума)

        # ── Ибораҳоро аввал ёб (phrase-first) ────────────────────────────
        # phrase_wr_map: form_lower → (dks, "dialect_phrase", lit_orig)
        phrase_wr_map: dict[str, tuple] = {}
        phrase_scores: dict[str, int]   = {}
        for form, lit_orig, dks in db.detect_phrases(text.lower()):
            phrase_wr_map[form] = (dks, "dialect_phrase", lit_orig)
            for dk in dks:
                phrase_scores[dk] = phrase_scores.get(dk, 0) + 1

        # ── Токенҳо барои SQL ──────────────────────────────────────────
        # Пайвандак-калимаҳоро ба қисматҳо ҷудо мекунем барои луғат
        compound_tokens = re.findall(r"[\wЀ-ӿ]+(?:-[\wЀ-ӿ]+)+", text, re.UNICODE)
        simple_tokens   = re.findall(r"[\wЀ-ӿ]+", text, re.UNICODE)

        # Луғати тарҷума — АВВАЛ санҷем (бартарияти олӣ, ҳама токен)
        tr_map = db.tr_translate_batch(simple_tokens)

        scores, word_results = db.detect_dialect(simple_tokens)
        # Ибора баллҳоро ба умумиге илова мекунем
        for dk, sc in phrase_scores.items():
            scores[dk] = scores.get(dk, 0) + sc

        # Морфологии иловагӣ барои нешинохташудаҳо
        unknown_toks = [tok for tok, m, wt in word_results if not m]
        morph_map    = db.morph_classify(unknown_toks)

        # Луғати тарҷума — ҳамаи токенҳоро иваз мекунем (на танҳо unknown)
        for tok in simple_tokens:
            tl = tok.lower()
            if tl in tr_map:
                morph_map[tl] = (["translator"], tr_map[tl], "translator")

        # Калимаҳоеро ки дар ибораҳо ёфта мешаванд низ ислоҳ мекунем
        for tok, m, wt in word_results:
            if m or wt != "unknown":
                continue
            if tok.lower() in morph_map:
                continue
            lit_w, dks = db.find_word_in_phrases(tok)
            if dks and lit_w.lower() != tok.lower():
                morph_map[tok.lower()] = (dks, lit_w, "dialect_phrase_word")
                for dk in dks:
                    scores[dk] = scores.get(dk, 0) + 1

        # wr_map: tl → (matched, wtype, lit_override)
        wr_map: dict[str, tuple] = {}
        for tok, m, wtype in word_results:
            wr_map.setdefault(tok.lower(), (m, wtype, None))
        # Ибораҳо
        wr_map.update(phrase_wr_map)
        # Морфология ва ибора-калима
        for tl, (dks, lit_f, mtype) in morph_map.items():
            if tl not in tr_map:          # translator-ро дасткорӣ накунем
                wr_map[tl] = (dks, mtype, lit_f)
                if "dialect" in mtype:
                    for dk in dks:
                        scores[dk] = scores.get(dk, 0) + 1
        # Луғати тарҷума — ОХИРда, олитарин бартарӣ (ҳеч чиз иваз карда наметавонад)
        for tl, lit in tr_map.items():
            wr_map[tl] = (["translator"], "translator", lit)

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

        # ── Миёна: таҳлили морфологӣ (реша / пешванд / пасванд) ────────────
        self._show_morph_mid(text, wr_map)

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

        replaced_cnt  = 0
        unchanged_cnt = 0
        unknown_words: list[str] = []   # калимаҳое ки дар база нестанд

        for tok, is_word in tokens:
            if not is_word:
                self.right_text.insert("end", tok)
                continue
            matched, wtype, lit_override = wr_map.get(tok.lower(), ([], "unknown", None))
            tag = self._next_tag()
            if not matched:
                if lit_override and lit_override.lower() != tok.lower():
                    # Кашидашавии садонок ислоҳ шуд (бародарм → бародарам)
                    replaced_cnt += 1
                    self.right_text.tag_configure(tag, foreground=CG,
                        font=("Segoe UI", 12, "bold"))
                    self.right_text.insert("end", _apply_case(tok, lit_override), (tag,))
                else:
                    # Дар база нест — адабии стандартӣ ҳисоб мешавад
                    unchanged_cnt += 1
                    tl = tok.lower()
                    if wtype == "unknown" and tl not in {w.lower() for w in unknown_words}:
                        unknown_words.append(tok)
                    self.right_text.tag_configure(tag, foreground=CL,
                        font=("Segoe UI", 12))
                    self.right_text.insert("end", tok, (tag,))
            elif wtype in ("literary", "literary_stem"):
                # Адабӣ — сиёҳ, бидуни тағйир
                unchanged_cnt += 1
                self.right_text.tag_configure(tag, foreground=CL,
                    font=("Segoe UI", 12))
                self.right_text.insert("end", tok, (tag,))
            else:
                # Лаҳҷавӣ → ислоҳ → сабз
                lit = lit_override or self._find_literary(tok, matched)
                if lit.lower() != tok.lower():
                    replaced_cnt += 1
                else:
                    unchanged_cnt += 1
                self.right_text.tag_configure(tag, foreground=CG,
                    font=("Segoe UI", 12, "bold"))
                self.right_text.insert("end", _apply_case(tok, lit), (tag,))

        # ── "ба/Ба + феъл" → "баъд/Баъд" дар right_text ─────────────────
        self._apply_ba_correction()

        self.right_text.configure(state="disabled")

        # ── Калимаҳои сермаъно зерхат мекунем ──────────────────────────
        self._mark_polysemy_words()

        # ── AI пешниҳодҳо: калимаҳои адабии ивазшуда ──────────────────
        _LIT_SKIP = {"literary", "literary_stem"}
        lit_replacements: list[str] = []
        for tok, is_word in tokens:
            if not is_word:
                continue
            matched, wtype, lit_override = wr_map.get(tok.lower(), ([], "unknown", None))
            if matched and wtype not in _LIT_SKIP:
                # Лаҳҷавии иваз шуда → шакли адабии он
                lit = lit_override or self._find_literary(tok, matched)
                if lit and lit.lower() != tok.lower():
                    lit_replacements.append(lit)
            elif lit_override and lit_override.lower() != tok.lower():
                # Кашидашавии садонок ислоҳшуда
                lit_replacements.append(lit_override)
        # Дубликатҳоро нест мекунем, тартибро нигоҳ медорем
        seen_lit: set[str] = set()
        unique_lit = []
        for w in lit_replacements:
            wl = w.lower()
            if wl not in seen_lit:
                seen_lit.add(wl)
                unique_lit.append(w)
        self._run_ai_suggest(unique_lit)

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
            _winner_line = "Ноҳия муайян нашуд"
        else:
            wd    = self.data["dialects"].get(best, {})
            conf  = int(best_sc / total * 100)
            color = self._dialect_colors.get(best, C["winner_fg"])
            self.winner_name.config(text=wd.get("name", best), fg=color)
            self.winner_region.config(text=wd.get("region", ""))
            self.conf_lbl.config(text=f"Эҳтимол: {conf}%  ·  {best_sc} калима")
            _winner_line = (f"Ноҳия: {wd.get('name', best)}"
                            + (f"  ({wd.get('region','')})" if wd.get("region") else "")
                            + f"  ·  Эҳтимол {conf}%")

        # ── Омори тарҷума ─────────────────────────────────────────────
        if hasattr(self, "_stats_lbl"):
            _total_w2 = replaced_cnt + unchanged_cnt
            _repl_pct = int(replaced_cnt / _total_w2 * 100) if _total_w2 else 0
            _unch_pct = 100 - _repl_pct
            self._stats_lbl.config(text=(
                f"✔ Иваз шуд: {replaced_cnt} кал. ({_repl_pct}%)  "
                f"◌ Боқӣ монд: {unchanged_cnt} кал. ({_unch_pct}%)\n"
                f"Адабӣ: {lit_pct}%   Лаҳҷавӣ: {dial_pct}%   ·   {_winner_line}"
            ))
        if hasattr(self, "_unknown_lbl"):
            if unknown_words:
                _unk_show = ", ".join(unknown_words[:8])
                _unk_more = f"  +{len(unknown_words)-8} дигар" if len(unknown_words) > 8 else ""
                self._unknown_lbl.config(
                    text=f"⚠ Дар база нест: {_unk_show}{_unk_more}")
            else:
                self._unknown_lbl.config(text="")

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
            names    = ", ".join(
                self.data["dialects"].get(m, {}).get("name", m)
                for m in matched)
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

    # ══════════════════════════════════════════════════════════════════════
    # ИСЛОҲИ "ба/Ба + феъл" → "баъд/Баъд" дар равзанаи 3
    # ══════════════════════════════════════════════════════════════════════
    def _run_ai_suggest(self, lit_words: list[str]):
        """Калимаҳои адабии ивазшударо мегирад ва аз ҳамаи базаҳо монандҳоро меёбад."""
        from ai_analyzer import suggest_similar

        if not lit_words:
            self._update_ai_sugg("")
            return

        self._ai_spin_lbl.config(text="⏳ ҷустуҷу...")
        self._ai_sugg_text.configure(state="normal")
        self._ai_sugg_text.delete("1.0", "end")
        self._ai_sugg_text.insert("end", "Ҷустуҷу идома дорад...")
        self._ai_sugg_text.configure(state="disabled")

        db_rows = db.get_all_for_suggest()

        def _ok(txt):
            self.after(0, lambda: self._update_ai_sugg(txt))
        def _err(msg):
            self.after(0, lambda: self._update_ai_sugg(f"⚠ {msg}"))

        suggest_similar(lit_words, db_rows, self._api_key, _ok, _err)

    def _update_ai_sugg(self, text: str):
        """Натиҷаи AI-пешниҳодро дар панел нишон медиҳад."""
        self._ai_spin_lbl.config(text="")
        self._ai_sugg_text.configure(state="normal")
        self._ai_sugg_text.delete("1.0", "end")
        self._ai_sugg_text.insert("end", text)
        self._ai_sugg_text.configure(state="disabled")

    # ── Text-to-Speech ─────────────────────────────────────────────────────
    def _speak_right(self):
        """Ҳар клик: агар кор мекунад — мебозмедорад ва аз нав шурӯъ мекунад."""
        import threading

        # Ҳамеша аввал мебозмедорем — ҳеҷ гоҳ рӯи ҳам нест
        self._tts_stop()

        text = self.right_text.get("1.0", "end").strip()
        if not text:
            return

        # Сессияи нав — thread-и кӯҳна UI-ро дигар навсозӣ намекунад
        self._tts_session = getattr(self, "_tts_session", 0) + 1
        sid = self._tts_session

        self._tts_active = True
        self._tts_btn.config(text="⏹", bg="#c0392b", activebackground="#a93226")

        def _run():
            try:
                import subprocess, re
                safe = re.sub(r'["\'\n\r]', ' ', text)[:1000]
                proc = subprocess.Popen(
                    ["powershell", "-WindowStyle", "Hidden", "-Command",
                     "Add-Type -AssemblyName System.Speech; "
                     "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                     f'$s.Speak("{safe}")'],
                    creationflags=subprocess.CREATE_NO_WINDOW)
                self._tts_proc = proc
                proc.wait()
            except Exception:
                try:
                    import pyttsx3
                    eng = pyttsx3.init()
                    self._tts_engine = eng
                    eng.setProperty("rate", 145)
                    eng.say(text)
                    eng.runAndWait()
                except Exception:
                    pass
            # Танҳо агар ин session ҳанӯз фаъол бошад UI-ро навсозӣ мекунем
            if getattr(self, "_tts_session", 0) == sid:
                self.after(0, self._tts_done)

        self._tts_thread = threading.Thread(target=_run, daemon=True)
        self._tts_thread.start()

    def _tts_stop(self):
        """Ҷараёни TTS-ро дарҳол мебозмедорад."""
        proc = getattr(self, "_tts_proc", None)
        if proc:
            try: proc.terminate()
            except Exception: pass
            self._tts_proc = None
        eng = getattr(self, "_tts_engine", None)
        if eng:
            try: eng.stop()
            except Exception: pass
            self._tts_engine = None
        self._tts_active = False

    def _tts_done(self):
        """Пас аз хатми хондан тугмаро барқарор мекунад."""
        self._tts_active = False
        if hasattr(self, "_tts_btn"):
            self._tts_btn.config(text="🔊", bg="#5dade2", activebackground="#2e86c1")

    # ══════════════════════════════════════════════════════════════════════
    # ПЕШНИҲОДИ КАЛИМА — клики мушак боло/ба калима
    # ══════════════════════════════════════════════════════════════════════
    def _make_chip_strip(self, parent, bg, side="top"):
        """Полоси уфуқии чипҳои пешниҳодиро месозад.
        Ҳамеша пакед аст (баландии 0 ҳангоми холӣ), то мавқеъаш нигоҳ дошта шавад."""
        outer = tk.Frame(parent, bg=bg)
        outer.pack(side=side, fill="x")
        cv = tk.Canvas(outer, height=0, bg=bg, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="horizontal", command=cv.xview)
        cv.configure(xscrollcommand=sb.set)
        inner = tk.Frame(cv, bg=bg)
        cv.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: cv.configure(scrollregion=cv.bbox("all")))
        sb.pack(side="bottom", fill="x")
        cv.pack(fill="x", expand=True)
        return outer, cv, inner

    def _show_ac_strip(self, strip, cv, inner, rows, on_click):
        """Чипҳоро нишон медиҳад (бе ҳарфи лотинӣ) ё полосро холӣ мегузорад."""
        import re as _re
        for w in inner.winfo_children():
            w.destroy()
        valid = []
        for row in (rows or []):
            label = row.get("_label") or row.get("literary", "") or row.get("dialect_form", "")
            if not label or _re.search(r"[a-zA-Z]", label):
                continue   # ҳарфи лотинӣ — нишон надеҳ
            valid.append((label, row))
        if not valid:
            cv.configure(height=0)
            return
        for label, row in valid:
            btn = tk.Button(
                inner, text=label,
                font=("Segoe UI", 9), relief="flat",
                bg="#dce8f7", fg="#1a3a5c",
                activebackground="#aac8ef",
                padx=7, pady=3, cursor="hand2",
                command=lambda r=row: on_click(r))
            btn.pack(side="left", padx=2, pady=2)
        cv.configure(height=36)
        cv.update_idletasks()
        cv.configure(scrollregion=cv.bbox("all"))

    @staticmethod
    def _word_at_coord(widget: tk.Text, x: int, y: int) -> tuple[str, str, str]:
        """(ws, we, word) аз координатаи пикселӣ. Дар widget-и disabled ҳам кор мекунад."""
        idx = widget.index(f"@{x},{y}")
        line_no, col = map(int, idx.split("."))
        line = widget.get(f"{line_no}.0", f"{line_no}.end")
        col = min(col, len(line))
        start = col
        while start > 0 and line[start - 1].isalpha():
            start -= 1
        end = col
        while end < len(line) and line[end].isalpha():
            end += 1
        return f"{line_no}.{start}", f"{line_no}.{end}", line[start:end]

    def _inp_click(self, event):
        """Клики мушак дар равзанаи 1 — монандҳо дар панели Вариантҳо."""
        try:
            ws, we, word = self._word_at_coord(self.inp, event.x, event.y)
        except (tk.TclError, ValueError, IndexError):
            return
        if len(word) < 2:
            return
        self._ac_source_w1 = (ws, we)
        raw = db.search_autocomplete_all(word, limit=16)
        expanded: list[dict] = []
        seen: set[str] = set()
        for row in raw:
            for form in (row.get("dialect_form", "").strip(),
                         row.get("literary", "").strip()):
                if form and form not in seen:
                    seen.add(form)
                    expanded.append({**row, "_label": form})
        self._show_ac_in_var(expanded, word)

    def _right_click(self, event):
        """Клики мушак дар равзанаи 3 — монандҳо ҳамчун chips зери равзанаи 3."""
        import re as _re
        try:
            ws, we, word = self._word_at_coord(self.right_text, event.x, event.y)
        except (tk.TclError, ValueError, IndexError):
            return
        if len(word) < 2:
            if hasattr(self, "_typing_right_strip"):
                self._show_ac_strip(
                    self._typing_right_strip, self._typing_right_cv,
                    self._typing_right_inner, [], None)
            return
        self._ac_source_w3 = (ws, we)
        rows = db.search_autocomplete_all(word, limit=14)
        filtered: list[dict] = []
        seen: set[str] = set()
        for r in rows:
            for form in (r.get("literary", "").strip(), r.get("dialect_form", "").strip()):
                if form and form not in seen and not _re.search(r"[a-zA-Z]", form):
                    seen.add(form)
                    filtered.append({**r, "_label": form})
        self._show_ac_strip(
            self._typing_right_strip, self._typing_right_cv, self._typing_right_inner,
            filtered, lambda r: self._ac3_click(r))

    def _show_ac_in_var(self, rows, word):
        """Монандҳои равзанаи 1-ро дар панели 'Вариантҳо' нишон медиҳад."""
        import re as _re
        for w in self._var_frame.winfo_children():
            w.destroy()
        filtered = [r for r in rows
                    if not _re.search(r'[a-zA-Z]', r.get("_label") or "")]
        if not filtered:
            self._var_title_l.config(
                text=f"«{word}» — монанд калима ёфт нашуд")
            return
        self._var_title_l.config(
            text=f"«{word}» — монанд калимаҳо (пахш кунед):")
        for row in filtered:
            lbl = row.get("_label", "")
            if not lbl:
                continue
            btn = tk.Button(
                self._var_frame, text=lbl,
                font=("Segoe UI", 10), bg="#e8f8f5", fg="#1a6b3a",
                relief="solid", bd=1, padx=8, pady=3,
                cursor="hand2",
                command=lambda r=row: self._ac1_click(r))
            btn.pack(side="left", padx=3, pady=2)
        self._var_canvas.update_idletasks()
        self._var_canvas.configure(
            scrollregion=self._var_canvas.bbox("all"))

    def _show_ac_in_ai(self, rows, word):
        """Монандҳои равзанаи 3-ро дар панели 'Пешниҳодҳои зеҳни сунъӣ' нишон медиҳад."""
        import re as _re
        self._ai_sugg_text.configure(state="normal")
        self._ai_sugg_text.delete("1.0", "end")
        self._ai_spin_lbl.config(text="")
        filtered = [r for r in rows
                    if not _re.search(r'[a-zA-Z]',
                                      r.get("literary") or r.get("dialect_form") or "")]
        if not filtered:
            self._ai_sugg_text.insert(
                "end", f"«{word}» — монанд калима ёфт нашуд")
            self._ai_sugg_text.configure(state="disabled")
            return
        self._ai_sugg_text.insert(
            "end", f"«{word}» — монанд калимаҳо:\n",
            ("hdr_tag",))
        self._ai_sugg_text.tag_configure(
            "hdr_tag", font=("Segoe UI", 9, "bold"),
            foreground="#1a3a8f", spacing3=4)
        for i, row in enumerate(filtered):
            lbl = row.get("literary") or row.get("dialect_form", "")
            if not lbl:
                continue
            tag = f"_w3_{i}"
            self._ai_sugg_text.insert("end", f"  {lbl}", (tag,))
            self._ai_sugg_text.tag_configure(
                tag, foreground="#1a5fa8",
                font=("Segoe UI", 10, "underline"),
                spacing1=2)
            self._ai_sugg_text.tag_bind(
                tag, "<Button-1>",
                lambda e, r=row: self._ac3_click(r))
            self._ai_sugg_text.tag_bind(
                tag, "<Enter>",
                lambda e, t=tag: self._ai_sugg_text.tag_configure(
                    t, background="#ddeeff"))
            self._ai_sugg_text.tag_bind(
                tag, "<Leave>",
                lambda e, t=tag: self._ai_sugg_text.tag_configure(
                    t, background=""))
            self._ai_sugg_text.insert("end", "  ")
        self._ai_sugg_text.configure(state="disabled")

    def _ac1_click(self, row: dict):
        """Калимаи интихобшударо дар равзанаи 1 иваз мекунад."""
        replacement = row.get("_label") or row.get("dialect_form") or row.get("literary", "")
        if not replacement or not hasattr(self, "_ac_source_w1") or self._ac_source_w1 is None:
            return
        ws, we = self._ac_source_w1
        try:
            original = self.inp.get(ws, we)
            self.inp.delete(ws, we)
            self.inp.insert(ws, _apply_case(original, replacement))
            self.inp.mark_set(tk.INSERT, f"{ws}+{len(replacement)}c")
        except tk.TclError:
            pass
        self._ac_source_w1 = None
        for w in self._var_frame.winfo_children():
            w.destroy()
        self._var_title_l.config(text="Вариантҳо — калимаро пахш кунед:")
        self._on_key()

    def _ac3_click(self, row: dict):
        """Калимаи интихобшударо дар равзанаи 3 иваз мекунад."""
        replacement = row.get("_label") or row.get("literary") or row.get("dialect_form", "")
        if not replacement or not hasattr(self, "_ac_source_w3") or self._ac_source_w3 is None:
            return
        ws, we = self._ac_source_w3
        self.right_text.configure(state="normal")
        try:
            original = self.right_text.get(ws, we)
            self.right_text.delete(ws, we)
            self.right_text.insert(ws, _apply_case(original, replacement))
        except tk.TclError:
            pass
        finally:
            self.right_text.configure(state="disabled")
        self._ac_source_w3 = None
        if hasattr(self, "_typing_right_strip"):
            self._show_ac_strip(
                self._typing_right_strip, self._typing_right_cv,
                self._typing_right_inner, [], None)

    # ══════════════════════════════════════════════════════════════════════
    # СЕРМАЪНО — клики рост дар равзанаи 3
    # ══════════════════════════════════════════════════════════════════════
    def _mark_polysemy_words(self):
        """Калимаҳои сермаъноро дар равзанаи 3 зерхат мекунад.
        Муқоиса бо қисми БАЪДИ '#' дар сутуни meaning анҷом мешавад."""
        import re as _re
        self.right_text.tag_remove("poly_mark", "1.0", "end")
        poly_map = db.get_polysemy_matches()   # {баъди_#: [пеш аз_#, ...]}
        if not poly_map:
            return
        content = self.right_text.get("1.0", "end")
        found = False
        for m in _re.finditer(r"[^\W\d_]+", content, _re.UNICODE):
            if m.group(0).lower() in poly_map:
                self.right_text.tag_add("poly_mark",
                    f"1.0+{m.start()}c", f"1.0+{m.end()}c")
                found = True
        if found:
            # Тегро аз ҳама болотар мегузорем то зери тегҳои дигар пинҳон нашавад
            self.right_text.tag_raise("poly_mark")

    def _right_click_poly(self, event):
        """Клики рост дар равзанаи 3 — менюи вариантҳои сермаъно.
        Пешниҳод: қисми ПЕШ АЗ '#'; муқоиса бо қисми БАЪДИ '#' буд."""
        try:
            ws, we, word = self._word_at_coord(self.right_text, event.x, event.y)
        except (tk.TclError, ValueError, IndexError):
            return
        if len(word) < 2:
            return
        poly_map = db.get_polysemy_matches()
        alts = poly_map.get(word.lower(), [])
        if not alts:
            return
        menu = tk.Menu(self, tearoff=0, font=("Segoe UI", 10))
        menu.add_command(label=f"  {word}", state="disabled",
                         font=("Segoe UI", 10, "bold"))
        menu.add_separator()
        for alt in alts:
            menu.add_command(
                label=f"  {alt}",
                command=lambda a=alt, w=ws, e=we: self._poly_replace(w, e, a))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _poly_replace(self, ws: str, we: str, replacement: str):
        """Калимаи сермаъноро дар равзанаи 3 иваз мекунад ва боз скан мекунад."""
        self.right_text.configure(state="normal")
        try:
            original = self.right_text.get(ws, we)
            self.right_text.delete(ws, we)
            self.right_text.insert(ws, _apply_case(original, replacement))
        except tk.TclError:
            pass
        finally:
            self.right_text.configure(state="disabled")
        # Дубора скан — шояд калимаи нав ҳам дар базаи сермаъно бошад
        self._mark_polysemy_words()

    # ── Speech-to-Text (нутқ → матн) ──────────────────────────────────────
    # Лотинии тоҷикӣ → Кириллии тоҷикӣ
    _LAT2CYR = [
        # Диграфҳо аввал
        ("gh", "ғ"), ("kh", "х"), ("sh", "ш"), ("ch", "ч"),
        ("zh", "ж"), ("ts", "тс"), ("yo", "ё"),
        ("ii", "ӣ"), ("uu", "ӯ"),
        # Ҳарфҳои танҳо
        ("a", "а"), ("b", "б"), ("d", "д"), ("e", "е"), ("f", "ф"),
        ("g", "г"), ("h", "ҳ"), ("i", "и"), ("j", "ҷ"), ("k", "к"),
        ("l", "л"), ("m", "м"), ("n", "н"), ("o", "о"), ("p", "п"),
        ("q", "қ"), ("r", "р"), ("s", "с"), ("t", "т"), ("u", "у"),
        ("v", "в"), ("w", "в"), ("x", "х"), ("y", "й"), ("z", "з"),
    ]

    # Номи ҳарфҳо → ҳарфи воқеӣ (корбар номи ҳарфро мегӯяд)
    _CHAR_NAMES: dict = {
        "қоф": "қ", "қаф": "қ", "qof": "қ", "qaf": "қ",
        "ҷим": "ҷ", "ҷем": "ҷ", "jim": "ҷ", "jem": "ҷ",
        "ии": "ӣ", "ии борик": "ӣ", "и борик": "ӣ",
        "ҳе": "ҳ", "ҳо": "ҳ", "he": "ҳ", "ha": "ҳ",
        "ғайн": "ғ", "ғаин": "ғ", "ghajn": "ғ", "ghayn": "ғ",
        "уу": "ӯ", "уу гурда": "ӯ", "у гурда": "ӯ",
        # Агар Whisper матни русиро бидиҳад
        "це": "қ", "же": "ҷ", "ха": "ҳ", "хе": "ҳ",
    }

    # Ислоҳи матни Кириллии стандартии Whisper
    _CYR_CORRECTIONS: list = [
        ("дж", "ҷ"), ("дз", "ҷ"),
        ("гх", "ғ"), ("гь", "ғ"),
        ("хх", "ҳ"),
        ("й й", "ӣ"),
    ]

    @staticmethod
    def _to_cyrillic(text: str) -> str:
        """Матни лотинии тоҷикиро ба Кириллӣ табдил медиҳад."""
        # Агар Кириллӣ аллакай зиёд бошад — тағйир надиҳ
        cyr = sum(1 for c in text if "Ѐ" <= c <= "ӿ")
        lat = sum(1 for c in text if c.isalpha() and c.isascii())
        if cyr >= lat:
            return text

        result = []
        tl = text.lower()
        i = 0
        while i < len(tl):
            matched = False
            for lat_seq, cyr_char in DialectApp._LAT2CYR:
                if tl[i:i + len(lat_seq)] == lat_seq:
                    # Сармо нигоҳ дорем
                    if text[i].isupper():
                        result.append(cyr_char.upper())
                    else:
                        result.append(cyr_char)
                    i += len(lat_seq)
                    matched = True
                    break
            if not matched:
                result.append(text[i])
                i += 1
        return "".join(result)

    @staticmethod
    def _post_process_voice(text: str) -> str:
        """Матни шинохташударо барои ҳарфҳои махсуси тоҷикӣ ислоҳ мекунад."""
        t = text.strip()
        key = t.lower()
        # Агар корбар номи ҳарфро гуфта бошад — ҳарфи воқеӣро бидеҳ
        if key in DialectApp._CHAR_NAMES:
            return DialectApp._CHAR_NAMES[key]
        # Ислоҳи хатоҳои маъмули Whisper
        for wrong, right in DialectApp._CYR_CORRECTIONS:
            t = t.replace(wrong, right)
        return t

    def _start_voice_input(self):
        """Микрофонро фаъол мекунад ва нутқро ба тоҷикии Кириллӣ табдил медиҳад.
        Марҳила 1 — Whisper (офлайн, тоҷикии нативӣ).
        Марҳила 2 — Google STT + транслитератсия (захира).
        """
        import threading

        if self._mic_recording:
            return

        self._mic_recording = True
        if hasattr(self, "_mic_btn"):
            self._mic_btn.config(text="⏺", bg="#c0392b", activebackground="#a93226")

        def _listen():
            import tempfile, os as _os
            text = None
            audio_obj = None  # sr.AudioData — захира барои Google

            try:
                import speech_recognition as sr
                r = sr.Recognizer()
                r.energy_threshold = 300
                r.dynamic_energy_threshold = True

                with sr.Microphone() as source:
                    r.adjust_for_ambient_noise(source, duration=0.4)
                    self.after(0, lambda: self._mic_btn.config(text="🔴", bg="#e74c3c", activebackground="#c0392b") if hasattr(self, "_mic_btn") else None)
                    audio_obj = r.listen(source, timeout=10, phrase_time_limit=20)

                # ── Марҳила 1: Whisper ──────────────────────────────────
                try:
                    from faster_whisper import WhisperModel

                    # Модел бори аввал боргузорӣ мешавад (tiny ≈ 75 МБ)
                    if not hasattr(DialectApp, "_whisper_model"):
                        self.after(0, lambda: self._mic_btn.config(text="⚙", bg="#e67e22", activebackground="#ca6f1e") if hasattr(self, "_mic_btn") else None)
                        DialectApp._whisper_model = WhisperModel(
                            "tiny", device="cpu", compute_type="int8")

                    wav = audio_obj.get_wav_data(
                        convert_rate=16000, convert_width=2)
                    tmp = tempfile.NamedTemporaryFile(
                        suffix=".wav", delete=False)
                    tmp.write(wav); tmp.close()
                    try:
                        segs, _ = DialectApp._whisper_model.transcribe(
                            tmp.name, language="tg", beam_size=5)
                        text = " ".join(s.text.strip() for s in segs).strip()
                        if text:
                            text = DialectApp._post_process_voice(text)
                    finally:
                        _os.unlink(tmp.name)
                except Exception:
                    pass

                # ── Марҳила 2: Google STT + транслитератсия ─────────────
                if not text and audio_obj:
                    for lang in ("ru-RU", "tg-TJ"):
                        try:
                            raw = r.recognize_google(audio_obj, language=lang)
                            text = DialectApp._post_process_voice(
                                DialectApp._to_cyrillic(raw))
                            break
                        except Exception:
                            continue

            except Exception:
                pass
            finally:
                if text:
                    self.after(0, lambda t=text: self._insert_voice_text(t))
                self.after(0, self._mic_done)

        threading.Thread(target=_listen, daemon=True).start()

    def _insert_voice_text(self, text: str):
        """Матни шинохташударо ба равзанаи 1 мегузорад ва таҳлил мекунад."""
        self.inp.configure(state="normal")
        cur = self.inp.get("1.0", "end").strip()
        if cur:
            self.inp.insert("end", " " + text)
        else:
            self.inp.delete("1.0", "end")
            self.inp.insert("1.0", text)
        self._on_key(None)

    def _mic_done(self):
        """Пас аз сабт тугмаро барқарор мекунад."""
        self._mic_recording = False
        if hasattr(self, "_mic_anim_id") and self._mic_anim_id:
            try:
                self.after_cancel(self._mic_anim_id)
            except Exception:
                pass
            self._mic_anim_id = None
        if hasattr(self, "_mic_btn"):
            self._mic_btn.config(text="🎤", bg="#3498db", activebackground="#2475a8")

    def _show_morph_mid(self, text: str, wr_map: dict | None = None):
        """
        Дар равзанаи дувум ҳар калимаро ба қисматҳо ҷудо мекунад:
          реша  → сурх+ғафс (агар калима лаҳҷавӣ бошад), вагарна сиёҳ+ғафс
          пешванди дуруст    → сиёҳ
          пешванди ношинохта → сурх+ғафс
          пасванди дуруст    → сиёҳ
          пасванди ношинохта → сурх+ғафс
          реша ёфт нашуд     → хокистарӣ
        """
        _DIALECT_TYPES = {"dialect", "both", "dialect_phrase",
                          "dialect_stem", "elision_corrected"}

        conn = db.get_connection()
        root_rows = conn.execute(
            "SELECT lower(root) AS r FROM roots"
            " ORDER BY length(root) DESC, root ASC"
        ).fetchall()
        all_roots  = [r["r"] for r in root_rows if len(r["r"]) >= 2]
        prefix_set = {r["prefix"].lower()
                      for r in conn.execute("SELECT prefix FROM prefixes").fetchall()}
        suffix_set = {r["suffix"].lower()
                      for r in conn.execute("SELECT suffix FROM suffixes").fetchall()}
        conn.close()

        CK = C["text"]     # сиёҳ  — адабӣ / стандартӣ
        CR = "#c0392b"     # сурх  — лаҳҷавӣ / ношинохта
        CN = C["neutral"]  # хокистарӣ — реша нест
        FN = ("Segoe UI", 12)
        FB = ("Segoe UI", 12, "bold")

        self.mid_text.configure(state="normal")
        self.mid_text.delete("1.0", "end")
        self.mid_text.tag_configure("m_root_lit",  foreground=CK, font=FB)
        self.mid_text.tag_configure("m_root_dial", foreground=CR, font=FB)
        self.mid_text.tag_configure("m_pfx_ok",    foreground=CK, font=FN)
        self.mid_text.tag_configure("m_pfx_bad",   foreground=CR, font=FB)
        self.mid_text.tag_configure("m_sfx_ok",    foreground=CK, font=FN)
        self.mid_text.tag_configure("m_sfx_bad",   foreground=CR, font=FB)
        self.mid_text.tag_configure("m_none",       foreground=CN, font=FN)

        for tok, is_word in _tokenize(text):
            if not is_word:
                self.mid_text.insert("end", tok)
                continue

            tl = tok.lower()

            # Лаҳҷавӣ будани калимаро аз wr_map муайян мекунем
            is_dialect = False
            if wr_map:
                matched, wtype, _ = wr_map.get(tl, ([], "unknown", None))
                is_dialect = bool(matched) and wtype in _DIALECT_TYPES

            # Дарозтарин решаро, ки дар калима ҳаст, меёбем
            found_root = None
            root_pos   = -1
            for root in all_roots:
                idx = tl.find(root)
                if idx != -1:
                    found_root = root
                    root_pos   = idx
                    break

            if found_root is None:
                # Реша нашуд — агар лаҳҷавӣ бошад сурх, вагарна хокистарӣ
                tag = "m_root_dial" if is_dialect else "m_none"
                self.mid_text.insert("end", tok, tag)
                continue

            root_end    = root_pos + len(found_root)
            prefix_part = tok[:root_pos]
            root_part   = tok[root_pos:root_end]
            suffix_part = tok[root_end:]

            if prefix_part:
                tag = ("m_pfx_ok" if prefix_part.lower() in prefix_set
                       else "m_pfx_bad")
                self.mid_text.insert("end", prefix_part, tag)

            # Реша: сурх агар лаҳҷавӣ, вагарна сиёҳ
            root_tag = "m_root_dial" if is_dialect else "m_root_lit"
            self.mid_text.insert("end", root_part, root_tag)

            if suffix_part:
                tag = ("m_sfx_ok" if suffix_part.lower() in suffix_set
                       else "m_sfx_bad")
                self.mid_text.insert("end", suffix_part, tag)

        self.mid_text.configure(state="disabled")

    def _load_verbs(self) -> set:
        """Ҳамаи феълҳоро аз базаи маълумот бармегардонад (шаклҳои адабӣ)."""
        conn = db.get_connection()
        verbs: set[str] = set()
        # Инфинитивҳо ва реша аз verb_forms
        for r in conn.execute(
                "SELECT lower(infinitive), lower(present_stem), lower(past_stem)"
                " FROM verb_forms").fetchall():
            for v in r:
                if v and v.strip():
                    verbs.add(v.strip())
        # Шаклҳои адабии феълҳо аз ҷадвали words
        for r in conn.execute(
                "SELECT lower(literary), lower(dialect_form)"
                " FROM words WHERE pos='феъл'").fetchall():
            for v in r:
                if v and v.strip():
                    verbs.add(v.strip())
        # Решаҳои феълӣ
        for r in conn.execute(
                "SELECT lower(root) FROM roots WHERE pos='феъл'").fetchall():
            if r[0] and r[0].strip():
                verbs.add(r[0].strip())
        conn.close()
        return verbs

    def _apply_ba_correction(self):
        """
        Дар матни равзанаи севвум "ба/Ба + феъл"-ро меёбад ва
        "ба/Ба"-ро бо "баъд/Баъд" иваз мекунад.
        Феъл будани калима аз рӯи базаи маълумот санҷида мешавад.
        """
        import re
        verbs = self._load_verbs()
        if not verbs:
            return

        full = self.right_text.get("1.0", "end-1c")
        if not full.strip():
            return

        # Тақсим ба токенҳо бо нигоҳ доштани фосилаҳо
        parts = re.split(r'(\s+)', full)

        offset = 0
        replacements = []  # [(start_char, end_char, new_text)]

        i = 0
        while i < len(parts):
            tok = parts[i]
            if tok.lower() == "ба" and i + 2 < len(parts):
                # Аломатҳои китобатиро аз калимаи баъдӣ мебароем
                raw_next = parts[i + 2]
                next_word = re.sub(r'[^\wҷқҳғӯӣЧҚҲҒӮӢ]', '', raw_next,
                                   flags=re.UNICODE).lower()
                if next_word and next_word in verbs:
                    new_tok = "Баъд" if tok[0].isupper() else "баъд"
                    replacements.append((offset, offset + len(tok), new_tok))
            offset += len(tok)
            i += 1

        if not replacements:
            return

        # Иваз аз охир ба аввал (то мавқеъҳо дигар нашаванд)
        self.right_text.configure(state="normal")
        for start_c, end_c, new_tok in reversed(replacements):
            start_idx = f"1.0+{start_c}c"
            end_idx   = f"1.0+{end_c}c"
            existing_tags = self.right_text.tag_names(start_idx)
            self.right_text.delete(start_idx, end_idx)
            self.right_text.insert(start_idx, new_tok, existing_tags)
        self.right_text.configure(state="disabled")

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
        if hasattr(self, "_stats_lbl"):
            self._stats_lbl.config(text="")
        if hasattr(self, "_unknown_lbl"):
            self._unknown_lbl.config(text="")

        self._clear_variants()
        self._clear_rvar()
        self.char_lbl.config(text="0 ҳарф")
        self._tts_stop()
        self._tts_done()
        self._ai_spin_lbl.config(text="")
        self._ai_sugg_text.configure(state="normal")
        self._ai_sugg_text.delete("1.0", "end")
        self._ai_sugg_text.configure(state="disabled")

        self.analysis_text.configure(state="normal")
        self.analysis_text.delete("1.0", "end")
        self.analysis_text.insert("end",
            "Натиҷаи муайян намудани матн ба кадом ноҳия мувофиқат мекунад")
        self.analysis_text.configure(state="disabled")

        # Ҳар ду полоси автокомплитро холӣ мекунем
        if hasattr(self, "_ac1_strip"):
            self._show_ac_strip(self._ac1_strip, self._ac1_cv,
                                self._ac1_inner, [], None)
        if hasattr(self, "_ac3_strip"):
            self._show_ac_strip(self._ac3_strip, self._ac3_cv,
                                self._ac3_inner, [], None)

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
                _c = _load_contact()
                has_photo = bool(_c.get("photo", ""))
                cw = 340; ch = 270 if has_photo else 210
                csw, csh = cdlg.winfo_screenwidth(), cdlg.winfo_screenheight()
                cdlg.geometry(f"{cw}x{ch}+{(csw-cw)//2}+{(csh-ch)//2}")

                tk.Frame(cdlg, bg="#e67e22", height=3).pack(fill="x")
                tk.Label(cdlg, text="📞  Муроҷиат ба Админ",
                         font=("Segoe UI", 11, "bold"), bg=BG, fg="#e67e22").pack(pady=(14, 4))
                tk.Frame(cdlg, bg="#21262d", height=1).pack(fill="x", padx=16, pady=(0, 10))

                # ── Расм ────────────────────────────────────────────────
                _cv_ref = [None]
                if has_photo:
                    PSIZ = 70
                    try:
                        import base64, io as _io
                        raw = base64.b64decode(_c["photo"])
                        try:
                            from PIL import Image, ImageTk
                            img = Image.open(_io.BytesIO(raw)).convert("RGBA")
                            img = img.resize((PSIZ, PSIZ), Image.LANCZOS)
                            tk_img = ImageTk.PhotoImage(img)
                        except ImportError:
                            import tempfile, os as _os
                            tmp = tempfile.NamedTemporaryFile(
                                delete=False, suffix=".png")
                            tmp.write(raw); tmp.close()
                            tk_img = tk.PhotoImage(file=tmp.name)
                            _os.unlink(tmp.name)
                            fac = max(1, max(tk_img.width(),
                                            tk_img.height()) // PSIZ)
                            if fac > 1:
                                tk_img = tk_img.subsample(fac, fac)
                        _cv_ref[0] = tk_img
                        ph_lbl = tk.Label(cdlg, image=tk_img, bg=BG)
                        ph_lbl.image = tk_img
                        ph_lbl.pack(pady=(0, 6))
                    except Exception:
                        pass

                cf = tk.Frame(cdlg, bg=BG)
                cf.pack(fill="x", padx=20)
                cf.columnconfigure(1, weight=1)

                for row, (lbl, val) in enumerate([
                    ("👤 Ном:",   _c["name"]),
                    ("📧 Email:", _c["email"]),
                    ("📱 Тел:",   _c["phone"]),
                ]):
                    tk.Label(cf, text=lbl, bg=BG, fg="#8b949e",
                             font=("Segoe UI", 9)).grid(
                             row=row, column=0, sticky="e", padx=(0, 10), pady=5)
                    tk.Label(cf, text=val, bg=BG, fg=FG,
                             font=("Segoe UI", 9, "bold")).grid(
                             row=row, column=1, sticky="w", pady=5)

                def _copy_email():
                    cdlg.clipboard_clear()
                    cdlg.clipboard_append(_c["email"])
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
            _c2 = _load_contact()
            has_photo2 = bool(_c2.get("photo", ""))
            cw = 340; ch = 275 if has_photo2 else 220
            csw, csh = cdlg.winfo_screenwidth(), cdlg.winfo_screenheight()
            cdlg.geometry(f"{cw}x{ch}+{(csw-cw)//2}+{(csh-ch)//2}")

            tk.Frame(cdlg, bg="#e67e22", height=3).pack(fill="x")
            tk.Label(cdlg, text="📞  Муроҷиат ба Админ",
                     font=("Segoe UI", 11, "bold"),
                     bg=BG, fg="#e67e22").pack(pady=(14, 4))
            tk.Frame(cdlg, bg="#21262d", height=1).pack(fill="x", padx=16, pady=(0, 10))

            # ── Расм ────────────────────────────────────────────────────
            _cv2_ref = [None]
            if has_photo2:
                PSIZ2 = 70
                try:
                    import base64, io as _io
                    raw = base64.b64decode(_c2["photo"])
                    try:
                        from PIL import Image, ImageTk
                        img = Image.open(_io.BytesIO(raw)).convert("RGBA")
                        img = img.resize((PSIZ2, PSIZ2), Image.LANCZOS)
                        tk_img = ImageTk.PhotoImage(img)
                    except ImportError:
                        import tempfile, os as _os
                        tmp = tempfile.NamedTemporaryFile(
                            delete=False, suffix=".png")
                        tmp.write(raw); tmp.close()
                        tk_img = tk.PhotoImage(file=tmp.name)
                        _os.unlink(tmp.name)
                        fac = max(1, max(tk_img.width(),
                                        tk_img.height()) // PSIZ2)
                        if fac > 1:
                            tk_img = tk_img.subsample(fac, fac)
                    _cv2_ref[0] = tk_img
                    ph_lbl2 = tk.Label(cdlg, image=tk_img, bg=BG)
                    ph_lbl2.image = tk_img
                    ph_lbl2.pack(pady=(0, 6))
                except Exception:
                    pass

            cf = tk.Frame(cdlg, bg=BG)
            cf.pack(fill="x", padx=24)
            cf.columnconfigure(1, weight=1)
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
                cdlg.clipboard_append(_c2["email"])
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
        self.bind_all("<F1>", lambda e: self._show_help())

    # ══════════════════════════════════════════════════════════════════════
    # ДАСТУРАМАЛ — F1
    # ══════════════════════════════════════════════════════════════════════
    def _show_help(self):
        dlg = tk.Toplevel(self)
        dlg.title("Дастурамал")
        dlg.configure(bg=C["bg"])
        dlg.resizable(False, False)
        dlg.grab_set()

        W = 520; H = 580
        dlg.geometry(f"{W}x{H}+{(dlg.winfo_screenwidth()-W)//2}"
                     f"+{(dlg.winfo_screenheight()-H)//2}")

        # ── Сарлавҳа ──────────────────────────────────────────────────────
        hdr = tk.Frame(dlg, bg="#1a3a5c", pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📖  Дастурамали барнома",
                 font=("Segoe UI", 14, "bold"),
                 bg="#1a3a5c", fg="white").pack()
        tk.Label(hdr, text="Лаҳҷаҳои Тоҷикистон  —  Версия 1.2.0",
                 font=("Segoe UI", 9), bg="#1a3a5c", fg="#aac8e8").pack()

        # ── Мундариҷа ─────────────────────────────────────────────────────
        canvas = tk.Canvas(dlg, bg=C["bg"], highlightthickness=0)
        sb = tk.Scrollbar(dlg, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True, padx=0)

        frame = tk.Frame(canvas, bg=C["bg"])
        canvas.create_window((0, 0), window=frame, anchor="nw")
        frame.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        def _scroll(e):
            canvas.yview_scroll(-1*(e.delta//120), "units")

        def _bind_scroll(widget):
            widget.bind("<MouseWheel>", _scroll)
            for child in widget.winfo_children():
                _bind_scroll(child)

        canvas.bind("<MouseWheel>", _scroll)
        frame.bind("<Configure>", lambda e: (
            canvas.configure(scrollregion=canvas.bbox("all")),
            _bind_scroll(frame)
        ))

        def section(title, color="#1a3a5c"):
            tk.Frame(frame, bg=color, height=2).pack(fill="x", padx=12, pady=(14,2))
            tk.Label(frame, text=title, font=("Segoe UI", 11, "bold"),
                     bg=C["bg"], fg=color, anchor="w").pack(fill="x", padx=14)

        def row(icon, text):
            r = tk.Frame(frame, bg=C["bg"])
            r.pack(fill="x", padx=18, pady=2)
            tk.Label(r, text=icon, font=("Segoe UI", 10),
                     bg=C["bg"], fg="#555", width=3, anchor="w").pack(side="left")
            tk.Label(r, text=text, font=("Segoe UI", 10),
                     bg=C["bg"], fg=C["text"], anchor="w", wraplength=420,
                     justify="left").pack(side="left", fill="x")

        # ── Дар бораи барнома ──────────────────────────────────────────────
        section("ℹ️  Дар бораи барнома", "#1a3a5c")
        row("👤", "Муаллиф:  Холмуродов Раҷабали")
        row("📅", "Сохта шуд:  2024 — 2025")
        row("🔖", "Версия:  1.2.0")
        row("📧", "Почта:  rajabaliit1995@mail.com")
        row("📞", "Телефон:  +992 985111995")
        row("🎯", "Мақсад:  Муайян кардани лаҳҷаи тоҷикии матн тавассути таҳлили луғавӣ")

        # ── Чи тавр истифода бурдан ───────────────────────────────────────
        section("🚀  Чи тавр истифода бурдан", "#27ae60")
        row("1️⃣", "Матни лаҳҷавиро дар майдони чап нависед ё paste кунед")
        row("2️⃣", "Тугмаи «Таҳлил» пахш кунед ё Ctrl+Enter")
        row("3️⃣", "Натиҷа дар тарафи рост нишон дода мешавад")
        row("4️⃣", "Лаҳҷаи мувофиқ бо фоиз муайян мешавад")
        row("5️⃣", "Калимаҳои лаҳҷавӣ бо ранг ишора мешаванд")

        # ── Тугмаҳои клавиатура ───────────────────────────────────────────
        section("⌨️  Тугмаҳои клавиатура", "#8e44ad")
        row("F1", "Ин дастурамал")
        row("Ctrl+Enter", "Таҳлил кардан")
        row("Ctrl+Z", "Тоза кардани матн")

        # ── Имконоти барнома ──────────────────────────────────────────────
        section("⚙️  Имконоти барнома", "#e67e22")
        row("📊", "Омор — оморҳои умумии луғат ва лаҳҷаҳо")
        row("📚", "Луғат — иловаи калимаҳои нав ба луғат")
        row("🤖", "AI — тавзеҳи иловагӣ аз тарафи зеҳни сунъӣ")
        row("🔑", "Парол — иваз кардани пароли худ")

        # ── Поён ──────────────────────────────────────────────────────────
        tk.Frame(frame, bg="#eee", height=1).pack(fill="x", padx=12, pady=(16, 4))
        tk.Label(frame, text="© 2024–2025  Холмуродов Раҷабали  |  Ҳуқуқ ҳифз аст",
                 font=("Segoe UI", 8), bg=C["bg"], fg=C["text3"]).pack(pady=(0, 12))

        # ── Тугмаи пӯшидан ────────────────────────────────────────────────
        tk.Button(dlg, text="✕  Пӯшидан", font=("Segoe UI", 10, "bold"),
                  bg="#1a3a5c", fg="white", relief="flat", cursor="hand2",
                  pady=8, command=dlg.destroy).pack(fill="x", padx=0, pady=0)

        dlg.wait_window()

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
            cw, ch = 420, 370
            csw = cdlg.winfo_screenwidth(); csh = cdlg.winfo_screenheight()
            cdlg.geometry(f"{cw}x{ch}+{(csw-cw)//2}+{(csh-ch)//2}")

            tk.Frame(cdlg, bg="#e67e22", height=3).pack(fill="x")
            tk.Label(cdlg, text="📞  Маълумоти тамос (Бақайдгирӣ)",
                     font=("Segoe UI", 10, "bold"),
                     bg=BG, fg="#e67e22").pack(pady=(12, 4))
            tk.Frame(cdlg, bg=BG3, height=1).pack(fill="x", padx=16, pady=(0, 8))

            cur = _load_contact()

            # ── Расм (аватар) ───────────────────────────────────────────
            PSIZ = 90
            photo_b64 = [cur.get("photo", "")]   # mutable container
            _ph_ref   = [None]                    # PhotoImage reference

            ph_row = tk.Frame(cdlg, bg=BG)
            ph_row.pack(pady=(0, 8))

            ph_canvas = tk.Canvas(ph_row, width=PSIZ, height=PSIZ,
                                  bg="#2d333b", highlightthickness=2,
                                  highlightbackground="#444c56")
            ph_canvas.pack(side="left", padx=(20, 14))

            def _draw_photo():
                ph_canvas.delete("all")
                b64 = photo_b64[0]
                if b64:
                    try:
                        import base64, io as _io
                        raw = base64.b64decode(b64)
                        try:
                            from PIL import Image, ImageTk
                            img = Image.open(_io.BytesIO(raw)).convert("RGBA")
                            img = img.resize((PSIZ, PSIZ), Image.LANCZOS)
                            tk_img = ImageTk.PhotoImage(img)
                        except ImportError:
                            import tempfile, os as _os
                            tmp = tempfile.NamedTemporaryFile(
                                delete=False, suffix=".png")
                            tmp.write(raw); tmp.close()
                            tk_img = tk.PhotoImage(file=tmp.name)
                            _os.unlink(tmp.name)
                            fac = max(1, max(tk_img.width(),
                                            tk_img.height()) // PSIZ)
                            if fac > 1:
                                tk_img = tk_img.subsample(fac, fac)
                        _ph_ref[0] = tk_img
                        ph_canvas.create_image(
                            PSIZ // 2, PSIZ // 2, image=tk_img)
                        return
                    except Exception:
                        pass
                # Placeholder
                ph_canvas.create_oval(4, 4, PSIZ-4, PSIZ-4,
                                      fill="#444c56", outline="#586069")
                ph_canvas.create_text(PSIZ//2, PSIZ//2, text="👤",
                                      font=("Segoe UI", 32), fill="#8b949e")

            _draw_photo()

            ph_btns = tk.Frame(ph_row, bg=BG)
            ph_btns.pack(side="left")

            def _pick_photo():
                from tkinter import filedialog
                path = filedialog.askopenfilename(
                    parent=cdlg, title="Расми профил интихоб кунед",
                    filetypes=[("Расм", "*.png *.jpg *.jpeg *.gif *.bmp"),
                               ("Ҳама", "*.*")])
                if not path:
                    return
                try:
                    import base64, io as _io
                    try:
                        from PIL import Image
                        img = Image.open(path).convert("RGBA")
                        img.thumbnail((300, 300), Image.LANCZOS)
                        buf = _io.BytesIO()
                        img.save(buf, format="PNG")
                        photo_b64[0] = base64.b64encode(
                            buf.getvalue()).decode()
                    except ImportError:
                        with open(path, "rb") as f:
                            photo_b64[0] = base64.b64encode(
                                f.read()).decode()
                    _draw_photo()
                except Exception:
                    pass

            def _del_photo():
                photo_b64[0] = ""
                _draw_photo()

            tk.Button(ph_btns, text="🖼  Расм интихоб",
                      command=_pick_photo,
                      font=("Segoe UI", 8, "bold"),
                      bg="#1a5276", fg="white", relief="flat",
                      cursor="hand2", padx=10, pady=5).pack(pady=(0, 6))
            tk.Button(ph_btns, text="🗑  Хариш",
                      command=_del_photo,
                      font=("Segoe UI", 8),
                      bg="#7a1a1a", fg="white", relief="flat",
                      cursor="hand2", padx=10, pady=4).pack()

            # ── Майдонҳои матн ──────────────────────────────────────────
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
            cmsg.pack(pady=(4, 2))

            def _do_save():
                d = {k: v.get().strip() for k, v in fields.items()}
                d["photo"] = photo_b64[0]
                _save_contact(d)
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
    # ══════════════════════════════════════════════════════════════════════
    # ЛУҒАТИ ТАРҶУМА
    # ══════════════════════════════════════════════════════════════════════
    def _show_translator(self):
        win = tk.Toplevel(self)
        win.title("📖 Луғати тарҷума — лаҳҷавӣ → адабӣ")
        win.configure(bg=C["bg"])
        win.geometry("700x520")
        win.minsize(560, 400)
        W, H = 700, 520
        win.geometry(f"{W}x{H}+{(win.winfo_screenwidth()-W)//2}+{(win.winfo_screenheight()-H)//2}")

        # ── Сарлавҳа ──────────────────────────────────────────────────────
        hdr = tk.Frame(win, bg="#1a6b3a", pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📖  Луғати тарҷума",
                 font=("Segoe UI", 13, "bold"),
                 bg="#1a6b3a", fg="white").pack()
        tk.Label(hdr, text="Калимаи лаҳҷавиро нависед — дар таҳлил ба адабӣ тарҷума мешавад",
                 font=("Segoe UI", 9), bg="#1a6b3a", fg="#a8d5b5").pack()

        # ── Ҷустуҷӯ ───────────────────────────────────────────────────────
        sf = tk.Frame(win, bg=C["bg"], pady=6)
        sf.pack(fill="x", padx=10)
        tk.Label(sf, text="🔍", font=("Segoe UI", 11),
                 bg=C["bg"]).pack(side="left")
        search_v = tk.StringVar()
        se = tk.Entry(sf, textvariable=search_v, font=("Segoe UI", 11),
                      relief="solid", bd=1, width=30)
        se.pack(side="left", padx=6)
        count_lbl = tk.Label(sf, text="", font=("Segoe UI", 9),
                             bg=C["bg"], fg=C["text3"])
        count_lbl.pack(side="left", padx=4)

        # ── Ҷадвал ────────────────────────────────────────────────────────
        cols = ("dialect_word", "literary", "note")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=16)
        tree.heading("dialect_word", text="Калимаи лаҳҷавӣ")
        tree.heading("literary",     text="Тарҷумаи адабӣ")
        tree.heading("note",         text="Изоҳ")
        tree.column("dialect_word", width=200, anchor="w")
        tree.column("literary",     width=200, anchor="w")
        tree.column("note",         width=200, anchor="w")
        vsb = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y", padx=(0,4))
        tree.pack(fill="both", expand=True, padx=(10,0), pady=4)

        # Маълумотро юклаш
        _rows_cache: list[dict] = []

        def _load(q=""):
            nonlocal _rows_cache
            tree.delete(*tree.get_children())
            _rows_cache = db.tr_get_all(q)
            for r in _rows_cache:
                tree.insert("", "end", iid=str(r["id"]),
                            values=(r["dialect_word"], r["literary"], r["note"]))
            count_lbl.config(text=f"{len(_rows_cache)} ёзув")

        search_v.trace_add("write", lambda *_: _load(search_v.get()))
        _load()

        # ── Тугмаҳо ───────────────────────────────────────────────────────
        btnf = tk.Frame(win, bg=C["bg"], pady=6)
        btnf.pack(fill="x", padx=10)

        def _btn(parent, text, cmd, bg, fg="white"):
            b = tk.Button(parent, text=text, command=cmd,
                          font=("Segoe UI", 9, "bold"),
                          bg=bg, fg=fg, relief="flat",
                          cursor="hand2", padx=10, pady=5)
            b.pack(side="left", padx=3)
            return b

        def _add_dialog(dialect_word=None, prefill_l="", edit_id=None,
                        prefill_d=""):
            # ADD mode with known word: shows read-only label + literary field only
            # ADD mode without word: shows both fields (user types both)
            # EDIT mode: always shows both fields
            is_edit = edit_id is not None
            dial_word = prefill_d if is_edit else (dialect_word or "").strip()
            # If no dialect word known, show both input fields
            need_dial_field = not dial_word

            d = tk.Toplevel(win)
            d.configure(bg=C["bg"])
            d.grab_set()
            d.resizable(False, False)

            if is_edit or need_dial_field:
                d.title("Таҳрир кардан" if is_edit else "Илова кардан")
                DW, DH = 380, 210
            else:
                dial_display = f"«{dial_word}»"
                d.title(f"Тарҷумаи {dial_display}")
                DW, DH = 380, 170

            d.geometry(f"{DW}x{DH}+{(d.winfo_screenwidth()-DW)//2}+{(d.winfo_screenheight()-DH)//2}")

            tk.Frame(d, bg="#1a6b3a", height=4).pack(fill="x")
            frm = tk.Frame(d, bg=C["bg"], padx=16, pady=12)
            frm.pack(fill="both", expand=True)

            def field(label, val=""):
                tk.Label(frm, text=label, font=("Segoe UI", 9, "bold"),
                         bg=C["bg"], fg=C["text"], anchor="w").pack(fill="x")
                v = tk.StringVar(value=val)
                e = tk.Entry(frm, textvariable=v, font=("Segoe UI", 11),
                             relief="solid", bd=1)
                e.pack(fill="x", pady=(2, 8))
                return v, e

            if is_edit or need_dial_field:
                # Show editable dialect field
                v_d, e_d = field("Калимаи лаҳҷавӣ:", prefill_d if is_edit else dial_word)
                if need_dial_field:
                    e_d.focus()
            else:
                # Dialect word is known — show as read-only label
                v_d = tk.StringVar(value=dial_word)
                tk.Label(frm, text=f"Лаҳҷавӣ: {dial_word}",
                         font=("Segoe UI", 10, "bold"),
                         bg=C["bg"], fg="#1a6b3a").pack(anchor="w", pady=(0, 6))

            v_l, e_l = field("Тарҷумаи адабӣ:", prefill_l)
            if not need_dial_field:
                e_l.focus()
            tajik_keys.walk_and_bind(d)

            msg = tk.Label(frm, text="", font=("Segoe UI", 9),
                           bg=C["bg"], fg="#c0392b")
            msg.pack()

            def _save():
                dw = v_d.get().strip()
                lw = v_l.get().strip()
                if not dw:
                    msg.config(text="⚠  Калимаи лаҳҷавӣ холӣ аст")
                    return
                if not lw:
                    msg.config(text="⚠  Тарҷумаи адабиро нависед")
                    return
                if is_edit:
                    res = db.tr_update(edit_id, dw, lw, "")
                else:
                    res = db.tr_add(dw, lw, "")
                if res == "ok":
                    d.destroy()
                    _load(search_v.get())
                elif res == "exists":
                    msg.config(text="⚠  Ин калима аллакай мавҷуд аст")
                else:
                    msg.config(text="⚠  Хато рӯй дод")

            bf = tk.Frame(frm, bg=C["bg"])
            bf.pack(fill="x")
            tk.Button(bf, text="💾 Сабт кардан", command=_save,
                      font=("Segoe UI", 10, "bold"),
                      bg="#1a6b3a", fg="white", relief="flat",
                      cursor="hand2", padx=12, pady=6).pack(side="left")
            tk.Button(bf, text="Бекор", command=d.destroy,
                      font=("Segoe UI", 9), bg=C["btn_clear"],
                      fg=C["btn_text"], relief="flat",
                      cursor="hand2", padx=10, pady=6).pack(side="left", padx=6)
            d.bind("<Return>", lambda e: _save())

        def _edit():
            sel = tree.selection()
            if not sel:
                return
            rid = int(sel[0])
            row = next((r for r in _rows_cache if r["id"] == rid), None)
            if row:
                _add_dialog(prefill_d=row["dialect_word"],
                            prefill_l=row["literary"],
                            edit_id=rid)

        def _delete():
            sel = tree.selection()
            if not sel:
                return
            rid = int(sel[0])
            row = next((r for r in _rows_cache if r["id"] == rid), None)
            if not row:
                return
            if messagebox.askyesno("Ҳазф", f"«{row['dialect_word']}» ҳазф шавад?",
                                   parent=win):
                db.tr_delete(rid)
                _load(search_v.get())

        _btn(btnf, "➕ Илова",
             lambda: _add_dialog(dialect_word=search_v.get()), "#1a6b3a")
        _btn(btnf, "✏️ Таҳрир", _edit,                 "#2471a3")
        _btn(btnf, "🗑 Ҳазф",   _delete,               "#c0392b")
        _btn(btnf, "✕ Пӯшидан", win.destroy,           "#555", "white")

        tree.bind("<Double-1>", lambda e: _edit())

        # Ҳарфҳои махсуси тоҷикӣ (ҷ қ ҳ ғ ӯ ӣ)
        tajik_keys.walk_and_bind(win)
        _load()

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

        # (номи нишондода, арзиши сутуни region дар база)
        REGIONS = [
            ("Вилояти Суғд",           "Суғд"),
            ("Вилояти Хатлон",         "Хатлон"),
            ("Ноҳияҳои тобеи ҷумҳурӣ", "НТМ"),
            ("ВМКБ — Бадахшон",        "ВМКБ"),
        ]
        _reg_map = {name: db_val for name, db_val in REGIONS}

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
            reg_display = reg_cb.get()
            reg_db = _reg_map.get(reg_display, "") if reg_display != "— Ҳама —" else ""
            s2    = db.stats()
            pd_   = {r["name"]: r["cnt"] for r in s2.get("per_dialect", [])}
            dlist = db.get_dialects()
            tv.delete(*tv.get_children())
            count = 0
            for i, d in enumerate(dlist):
                d_region = (d["region"] or "").strip()
                if q and q not in d["name"].lower() and q not in d["key"].lower() \
                       and q not in d_region.lower():
                    continue
                if reg_db and d_region != reg_db:
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
