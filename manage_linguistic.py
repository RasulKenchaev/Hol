# -*- coding: utf-8 -*-
"""
Идоракунии маълумоти луғавӣ:
  Калимаҳо · Решаҳо · Пешвандҳо · Пасвандҳо · Феълҳо · Сермаъноӣ
"""
import tkinter as tk
from tkinter import ttk, messagebox
import db
import tajik_keys

# ── палитра ──────────────────────────────────────────────────────────────────
BG   = "#0d1117"
BG2  = "#161b22"
BG3  = "#21262d"
BG4  = "#1c2128"
FG   = "#e6edf3"
FG2  = "#8b949e"
ACC  = "#58a6ff"
GRN  = "#3fb950"
RED  = "#f85149"
YLW  = "#d29922"
BRD  = "#30363d"
SEL  = "#1f6feb"
ORG  = "#d18616"

FN  = ("Segoe UI", 10)
FT  = ("Segoe UI", 10, "bold")
FS  = ("Segoe UI",  9)
FH  = ("Segoe UI", 13, "bold")


# ── ttk стили (ба номҳои стандартӣ, бо prefix барои тугмаҳо) ────────────────
def _apply_style():
    s = ttk.Style()
    try:
        s.theme_use("clam")
    except Exception:
        pass
    # Контейнерҳо
    s.configure("TFrame",           background=BG)
    s.configure("TLabel",           background=BG, foreground=FG, font=FN)
    # Notebook — стандартӣ, бидуни prefix
    s.configure("TNotebook",        background=BG3, borderwidth=0)
    s.configure("TNotebook.Tab",    background=BG3, foreground=FG2,
                                    padding=(14, 7), font=FN)
    s.map("TNotebook.Tab",          background=[("selected", BG2)],
                                    foreground=[("selected", FG)])
    # Treeview
    s.configure("Treeview",         background=BG2, foreground=FG,
                                    fieldbackground=BG2, rowheight=26, font=FN,
                                    borderwidth=0)
    s.configure("Treeview.Heading", background=BG3, foreground=ACC,
                                    relief="flat", font=FT)
    s.map("Treeview",               background=[("selected", SEL)],
                                    foreground=[("selected", FG)])
    # Entry / Combobox
    s.configure("TEntry",           fieldbackground=BG2, foreground=FG,
                                    insertcolor=FG, relief="flat", font=FN)
    s.configure("TCombobox",        fieldbackground=BG2, foreground=FG,
                                    selectbackground=SEL, font=FN)
    s.map("TCombobox",              fieldbackground=[("readonly", BG2)],
                                    foreground=[("readonly", FG)])
    # Scrollbar
    s.configure("TScrollbar",       background=BG3, troughcolor=BG2,
                                    arrowcolor=FG2, relief="flat")
    # Тугмаҳо бо prefix (3 навъ)
    s.configure("Std.TButton",      background=BG3, foreground=FG,
                                    relief="flat", padding=(8, 4), font=FN)
    s.map("Std.TButton",            background=[("active", "#2d333b")])
    s.configure("Acc.TButton",      background=SEL, foreground=FG,
                                    relief="flat", padding=(8, 4), font=FN)
    s.map("Acc.TButton",            background=[("active", "#388bfd")])
    s.configure("Del.TButton",      background="#3d1a1a", foreground=RED,
                                    relief="flat", padding=(8, 4), font=FN)
    s.map("Del.TButton",            background=[("active", "#5a1a1a")])


# ── ёрдамчиҳо ────────────────────────────────────────────────────────────────
def _fr(parent, **kw):
    return tk.Frame(parent, bg=BG, **kw)

def _fr2(parent, **kw):
    return tk.Frame(parent, bg=BG2, **kw)

def _lbl(parent, text, fg=FG2, bg=BG, **kw):
    return tk.Label(parent, text=text, fg=fg, bg=bg, font=FN, **kw)

def _entry(parent, width=22):
    e = ttk.Entry(parent, width=width)
    tajik_keys.apply_tajik_keys(e)
    return e

def _combo(parent, values, width=14):
    return ttk.Combobox(parent, values=values, width=width, state="readonly")

def _btn(parent, text, cmd, style="Std.TButton"):
    return ttk.Button(parent, text=text, command=cmd, style=style)

def _tree(parent, cols, widths, **kw):
    tv = ttk.Treeview(parent, columns=cols, show="headings", **kw)
    for col, w in zip(cols, widths):
        tv.heading(col, text=col, anchor="w")
        tv.column(col, width=w, anchor="w", minwidth=40)
    sb = ttk.Scrollbar(parent, orient="vertical", command=tv.yview)
    tv.configure(yscrollcommand=sb.set)
    tv.grid(row=0, column=0, sticky="nsew")
    sb.grid(row=0, column=1, sticky="ns")
    parent.rowconfigure(0, weight=1)
    parent.columnconfigure(0, weight=1)
    return tv

def _btn_row(parent):
    """Сатри тугмачаҳои стандартӣ → (кадр, add, edit, del, refresh)"""
    bf = _fr(parent)
    add = _btn(bf, "＋ Илова",  None, "Acc.TButton")
    add.pack(fill="x", pady=2)
    edt = _btn(bf, "✎ Вироиш", None)
    edt.pack(fill="x", pady=2)
    dlt = _btn(bf, "✕ Ҳазф",   None, "Del.TButton")
    dlt.pack(fill="x", pady=2)
    ref = _btn(bf, "⟳ Янгила", None)
    ref.pack(fill="x", pady=2)
    return bf, add, edt, dlt, ref


# ══════════════════════════════════════════════════════════════════════════════
# ҶАДВАЛИ КАЛИМАҲО (Words)
# ══════════════════════════════════════════════════════════════════════════════
class WordsTab(tk.Frame):
    def __init__(self, nb):
        super().__init__(nb, bg=BG)
        self._dialects = {d["key"]: d["name"] for d in db.get_dialects()}
        self._dk_keys  = [""] + list(self._dialects.keys())
        self._dk_names = ["— Ҳама —"] + list(self._dialects.values())
        self._build()

    def _build(self):
        # ── сатри ҷустуҷу ──────────────────────────────────────────────────
        sf = _fr(self)
        sf.pack(fill="x", padx=12, pady=(10, 4))

        _lbl(sf, "Ҷустуҷӯ:").pack(side="left")
        self._q = _entry(sf, 26)
        self._q.pack(side="left", padx=(4, 8))
        self._q.bind("<Return>",     lambda e: self.refresh())
        self._q.bind("<KeyRelease>", lambda e: self.refresh())

        _btn(sf, "＋ Илова", self._open_add, "Acc.TButton").pack(side="left", padx=(0, 2))
        _btn(sf, "⟳", self.refresh).pack(side="left")
        _btn(sf, "✕ Ҳазф", self._delete, "Del.TButton").pack(side="left", padx=(8, 2))

        self._count_lbl = _lbl(sf, "", fg=FG2)
        self._count_lbl.pack(side="right", padx=8)

        # ── ҷадвал ─────────────────────────────────────────────────────────
        tf = _fr(self)
        tf.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.tv = _tree(tf,
            cols=["Адабӣ", "Лаҳҷавӣ", "Лаҳҷа", "Ҷузъи нутқ"],
            widths=[180, 180, 260, 110],
            height=22)
        self.tv.tag_configure("odd", background=BG4)
        self.refresh()

    def refresh(self, _=None):
        q = self._q.get().strip().lower()

        conn = db.get_connection()
        sql  = """SELECT w.id, w.literary, w.dialect_form, d.name as dname,
                         w.pos, w.dialect_key
                  FROM words w
                  JOIN dialects d ON d.key = w.dialect_key
                  WHERE 1=1"""
        args = []
        if q:
            sql += " AND (lower(w.literary) LIKE ? OR lower(w.dialect_form) LIKE ?)"
            args += [f"%{q}%", f"%{q}%"]
        sql += " ORDER BY w.literary, d.name LIMIT 2000"
        rows = conn.execute(sql, args).fetchall()
        conn.close()

        self.tv.delete(*self.tv.get_children())
        for i, r in enumerate(rows):
            tag = ("odd",) if i % 2 else ()
            self.tv.insert("", "end", iid=str(r["id"]),
                values=(r["literary"], r["dialect_form"],
                        r["dname"], r["pos"] or ""),
                tags=tag)
        self._count_lbl.config(text=f"{len(rows)} калима")

    def _open_add(self):
        dlg = tk.Toplevel(self)
        dlg.title("＋ Калима илова кунед")
        dlg.geometry("360x140")
        dlg.configure(bg=BG)
        dlg.grab_set()
        dlg.resizable(False, False)

        grid = tk.Frame(dlg, bg=BG)
        grid.pack(fill="x", padx=18, pady=(18, 8))
        grid.columnconfigure(1, weight=1)

        _lbl(grid, "Адабӣ:").grid(row=0, column=0, sticky="e", padx=(0, 8), pady=6)
        e_lit = _entry(grid, 28)
        e_lit.grid(row=0, column=1, sticky="ew", pady=6)

        msg = _lbl(dlg, "", fg=RED)
        msg.pack(pady=(0, 4))

        def _save():
            lit = e_lit.get().strip()
            if not lit:
                msg.config(text="⚠  Майдон холӣ!"); return
            dk = self._dk_keys[1] if len(self._dk_keys) > 1 else ""
            db.add_word(dk, lit, lit, "words", "")
            self.refresh()
            dlg.destroy()

        bf = _fr(dlg)
        bf.pack(pady=(0, 12))
        _btn(bf, "✔ Захира", _save,       "Acc.TButton").pack(side="left", padx=6)
        _btn(bf, "Бекор",    dlg.destroy, "Std.TButton").pack(side="left", padx=6)

        e_lit.bind("<Return>", lambda _: _save())
        e_lit.focus_set()

    def _delete(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showwarning("Хато", "Калимаро интихоб кунед!"); return
        v = self.tv.item(sel[0], "values")
        if messagebox.askyesno("Ҳазф",
                f"«{v[0]}» → «{v[1]}» ({v[2]}) ҳазф карда шавад?"):
            db.delete_word(int(sel[0]))
            self.refresh()


# ══════════════════════════════════════════════════════════════════════════════
# Решаҳо
# ══════════════════════════════════════════════════════════════════════════════
class RootsTab(tk.Frame):
    def __init__(self, nb):
        super().__init__(nb, bg=BG)
        self._build()

    def _build(self):
        sf = _fr(self)
        sf.pack(fill="x", padx=12, pady=(10, 4))

        _lbl(sf, "Ҷустуҷӯ:").pack(side="left")
        self._q = _entry(sf, 22)
        self._q.pack(side="left", padx=(4, 8))
        self._q.bind("<Return>",     lambda e: self._do_search())
        self._q.bind("<KeyRelease>", lambda e: self._do_search())

        _btn(sf, "＋ Илова", self._open_add, "Acc.TButton").pack(side="left", padx=2)
        _btn(sf, "⟳ Ҳама",  self.refresh,   "Std.TButton").pack(side="left", padx=2)
        _btn(sf, "✕ Ҳазф",  self._delete,   "Del.TButton").pack(side="left", padx=6)

        self._count_lbl = _lbl(sf, "", fg=FG2)
        self._count_lbl.pack(side="right", padx=8)

        tf = _fr(self)
        tf.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.tv = _tree(tf, ["Реша", "Ҷузъи нутқ", "Маъно", "Эзоҳ"],
                        [130, 90, 200, 200], height=22)
        self.tv.tag_configure("odd", background=BG4)
        self.refresh()

    def refresh(self):
        self.tv.delete(*self.tv.get_children())
        rows = db.get_roots()
        for i, r in enumerate(rows):
            tag = ("odd",) if i % 2 else ()
            self.tv.insert("", "end", iid=str(r["id"]),
                values=(r["root"], r["pos"], r["meaning"], r["notes"]),
                tags=tag)
        self._count_lbl.config(text=f"{len(rows)} реша")

    def _do_search(self):
        q = self._q.get().strip().lower()
        if not q:
            self.refresh(); return
        self.tv.delete(*self.tv.get_children())
        rows = [r for r in db.get_roots()
                if q in str(r["root"]).lower() or q in str(r["meaning"]).lower()]
        for i, r in enumerate(rows):
            tag = ("odd",) if i % 2 else ()
            self.tv.insert("", "end", iid=str(r["id"]),
                values=(r["root"], r["pos"], r["meaning"], r["notes"]),
                tags=tag)
        self._count_lbl.config(text=f"{len(rows)} реша")

    def _open_add(self):
        dlg = tk.Toplevel(self)
        dlg.title("＋ Реша илова кунед")
        dlg.geometry("360x140")
        dlg.configure(bg=BG)
        dlg.grab_set()
        dlg.resizable(False, False)

        grid = tk.Frame(dlg, bg=BG)
        grid.pack(fill="x", padx=18, pady=(18, 8))
        grid.columnconfigure(1, weight=1)

        _lbl(grid, "Реша:").grid(row=0, column=0, sticky="e", padx=(0, 8), pady=6)
        e_root = _entry(grid, 28)
        e_root.grid(row=0, column=1, sticky="ew", pady=6)

        msg = _lbl(dlg, "", fg=RED)
        msg.pack(pady=(0, 4))

        def _save():
            root = e_root.get().strip()
            if not root:
                msg.config(text="⚠  Реша холӣ!"); return
            r = db.add_root(root, "", "", "")
            if r == "exists":
                msg.config(text="⚠  Ин реша аллакай мавҷуд аст!"); return
            self.refresh()
            dlg.destroy()

        bf = _fr(dlg)
        bf.pack(pady=(0, 12))
        _btn(bf, "✔ Захира", _save,       "Acc.TButton").pack(side="left", padx=6)
        _btn(bf, "Бекор",    dlg.destroy, "Std.TButton").pack(side="left", padx=6)

        e_root.bind("<Return>", lambda _: _save())
        e_root.focus_set()

    def _delete(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showwarning("Хато", "Реша интихоб кунед!"); return
        v = self.tv.item(sel[0], "values")
        if messagebox.askyesno("Ҳазф", f"«{v[0]}» ҳазф карда шавад?"):
            db.delete_root(int(sel[0]))
            self.refresh()


# ══════════════════════════════════════════════════════════════════════════════
# Пешвандҳо
# ══════════════════════════════════════════════════════════════════════════════
class PrefixesTab(tk.Frame):
    def __init__(self, nb):
        super().__init__(nb, bg=BG)
        self._build()

    def _build(self):
        sf = _fr(self)
        sf.pack(fill="x", padx=12, pady=(10, 4))

        _lbl(sf, "Ҷустуҷӯ:").pack(side="left")
        self._q = _entry(sf, 22)
        self._q.pack(side="left", padx=(4, 8))
        self._q.bind("<Return>",     lambda e: self._do_search())
        self._q.bind("<KeyRelease>", lambda e: self._do_search())

        _btn(sf, "＋ Илова", self._open_add, "Acc.TButton").pack(side="left", padx=2)
        _btn(sf, "⟳ Ҳама",  self.refresh,   "Std.TButton").pack(side="left", padx=2)
        _btn(sf, "✕ Ҳазф",  self._delete,   "Del.TButton").pack(side="left", padx=6)

        self._count_lbl = _lbl(sf, "", fg=FG2)
        self._count_lbl.pack(side="right", padx=8)

        tf = _fr(self)
        tf.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.tv = _tree(tf, ["Пешванд", "Маъно", "Категория"],
                        [120, 280, 160], height=22)
        self.tv.tag_configure("odd", background=BG4)
        self.refresh()

    def refresh(self):
        self.tv.delete(*self.tv.get_children())
        rows = db.get_prefixes()
        for i, r in enumerate(rows):
            tag = ("odd",) if i % 2 else ()
            self.tv.insert("", "end", iid=str(r["id"]),
                values=(r["prefix"], r["meaning"], r["category"]),
                tags=tag)
        self._count_lbl.config(text=f"{len(rows)} пешванд")

    def _do_search(self):
        q = self._q.get().strip().lower()
        if not q:
            self.refresh(); return
        self.tv.delete(*self.tv.get_children())
        rows = [r for r in db.get_prefixes()
                if q in str(r["prefix"]).lower() or q in str(r["meaning"]).lower()]
        for i, r in enumerate(rows):
            tag = ("odd",) if i % 2 else ()
            self.tv.insert("", "end", iid=str(r["id"]),
                values=(r["prefix"], r["meaning"], r["category"]),
                tags=tag)
        self._count_lbl.config(text=f"{len(rows)} пешванд")

    def _open_add(self):
        dlg = tk.Toplevel(self)
        dlg.title("＋ Пешванд илова кунед")
        dlg.geometry("360x140")
        dlg.configure(bg=BG)
        dlg.grab_set()
        dlg.resizable(False, False)

        grid = tk.Frame(dlg, bg=BG)
        grid.pack(fill="x", padx=18, pady=(18, 8))
        grid.columnconfigure(1, weight=1)

        _lbl(grid, "Пешванд:").grid(row=0, column=0, sticky="e", padx=(0, 8), pady=6)
        e_pref = _entry(grid, 28)
        e_pref.grid(row=0, column=1, sticky="ew", pady=6)

        msg = _lbl(dlg, "", fg=RED)
        msg.pack(pady=(0, 4))

        def _save():
            pref = e_pref.get().strip()
            if not pref:
                msg.config(text="⚠  Пешванд холӣ!"); return
            r = db.add_prefix(pref, "", "")
            if r == "exists":
                msg.config(text="⚠  Ин пешванд аллакай мавҷуд аст!"); return
            self.refresh()
            dlg.destroy()

        bf = _fr(dlg)
        bf.pack(pady=(0, 12))
        _btn(bf, "✔ Захира", _save,       "Acc.TButton").pack(side="left", padx=6)
        _btn(bf, "Бекор",    dlg.destroy, "Std.TButton").pack(side="left", padx=6)

        e_pref.bind("<Return>", lambda _: _save())
        e_pref.focus_set()

    def _delete(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showwarning("Хато", "Пешванд интихоб кунед!"); return
        v = self.tv.item(sel[0], "values")
        if messagebox.askyesno("Ҳазф", f"«{v[0]}» ҳазф карда шавад?"):
            db.delete_prefix(int(sel[0]))
            self.refresh()


# ══════════════════════════════════════════════════════════════════════════════
# Пасвандҳо
# ══════════════════════════════════════════════════════════════════════════════
class SuffixesTab(tk.Frame):
    def __init__(self, nb):
        super().__init__(nb, bg=BG)
        self._build()

    def _build(self):
        sf = _fr(self)
        sf.pack(fill="x", padx=12, pady=(10, 4))

        _lbl(sf, "Ҷустуҷӯ:").pack(side="left")
        self._q = _entry(sf, 22)
        self._q.pack(side="left", padx=(4, 8))
        self._q.bind("<Return>",     lambda e: self._do_search())
        self._q.bind("<KeyRelease>", lambda e: self._do_search())

        _btn(sf, "＋ Илова", self._open_add, "Acc.TButton").pack(side="left", padx=2)
        _btn(sf, "⟳ Ҳама",  self.refresh,   "Std.TButton").pack(side="left", padx=2)
        _btn(sf, "✕ Ҳазф",  self._delete,   "Del.TButton").pack(side="left", padx=6)

        self._count_lbl = _lbl(sf, "", fg=FG2)
        self._count_lbl.pack(side="right", padx=8)

        tf = _fr(self)
        tf.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.tv = _tree(tf, ["Пасванд", "Маъно", "Категория", "Аз", "Ба"],
                        [110, 200, 110, 80, 80], height=22)
        self.tv.tag_configure("odd", background=BG4)
        self.refresh()

    def refresh(self):
        self.tv.delete(*self.tv.get_children())
        rows = db.get_suffixes()
        for i, r in enumerate(rows):
            tag = ("odd",) if i % 2 else ()
            self.tv.insert("", "end", iid=str(r["id"]),
                values=(r["suffix"], r["meaning"], r["category"],
                        r["pos_from"], r["pos_to"]),
                tags=tag)
        self._count_lbl.config(text=f"{len(rows)} пасванд")

    def _do_search(self):
        q = self._q.get().strip().lower()
        if not q:
            self.refresh(); return
        self.tv.delete(*self.tv.get_children())
        rows = [r for r in db.get_suffixes()
                if q in str(r["suffix"]).lower() or q in str(r["meaning"]).lower()]
        for i, r in enumerate(rows):
            tag = ("odd",) if i % 2 else ()
            self.tv.insert("", "end", iid=str(r["id"]),
                values=(r["suffix"], r["meaning"], r["category"],
                        r["pos_from"], r["pos_to"]),
                tags=tag)
        self._count_lbl.config(text=f"{len(rows)} пасванд")

    def _open_add(self):
        dlg = tk.Toplevel(self)
        dlg.title("＋ Пасванд илова кунед")
        dlg.geometry("360x140")
        dlg.configure(bg=BG)
        dlg.grab_set()
        dlg.resizable(False, False)

        grid = tk.Frame(dlg, bg=BG)
        grid.pack(fill="x", padx=18, pady=(18, 8))
        grid.columnconfigure(1, weight=1)

        _lbl(grid, "Пасванд:").grid(row=0, column=0, sticky="e", padx=(0, 8), pady=6)
        e_suf = _entry(grid, 28)
        e_suf.grid(row=0, column=1, sticky="ew", pady=6)

        msg = _lbl(dlg, "", fg=RED)
        msg.pack(pady=(0, 4))

        def _save():
            suf = e_suf.get().strip()
            if not suf:
                msg.config(text="⚠  Пасванд холӣ!"); return
            r = db.add_suffix(suf, "", "", "", "")
            if r == "exists":
                msg.config(text="⚠  Ин пасванд аллакай мавҷуд аст!"); return
            self.refresh()
            dlg.destroy()

        bf = _fr(dlg)
        bf.pack(pady=(0, 12))
        _btn(bf, "✔ Захира", _save,       "Acc.TButton").pack(side="left", padx=6)
        _btn(bf, "Бекор",    dlg.destroy, "Std.TButton").pack(side="left", padx=6)

        e_suf.bind("<Return>", lambda _: _save())
        e_suf.focus_set()

    def _delete(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showwarning("Хато", "Пасванд интихоб кунед!"); return
        v = self.tv.item(sel[0], "values")
        if messagebox.askyesno("Ҳазф", f"«{v[0]}» ҳазф карда шавад?"):
            db.delete_suffix(int(sel[0]))
            self.refresh()


# ══════════════════════════════════════════════════════════════════════════════
# Феълҳо
# ══════════════════════════════════════════════════════════════════════════════
class VerbsTab(tk.Frame):
    def __init__(self, nb):
        super().__init__(nb, bg=BG)
        self._build()

    def _build(self):
        sf = _fr(self)
        sf.pack(fill="x", padx=12, pady=(10, 4))

        _lbl(sf, "Ҷустуҷӯ:").pack(side="left")
        self._q = _entry(sf, 22)
        self._q.pack(side="left", padx=(4, 8))
        self._q.bind("<Return>",     lambda e: self._do_search())
        self._q.bind("<KeyRelease>", lambda e: self._do_search())

        _btn(sf, "＋ Илова", self._open_add, "Acc.TButton").pack(side="left", padx=2)
        _btn(sf, "⟳ Ҳама",  self.refresh,   "Std.TButton").pack(side="left", padx=2)
        _btn(sf, "✕ Ҳазф",  self._delete,   "Del.TButton").pack(side="left", padx=6)

        self._count_lbl = _lbl(sf, "", fg=FG2)
        self._count_lbl.pack(side="right", padx=8)

        tf = _fr(self)
        tf.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.tv = _tree(tf, ["Масдар", "Ҳозира", "Гузашта", "Синф", "Реша"],
                        [150, 110, 110, 70, 130], height=22)
        self.tv.tag_configure("odd", background=BG4)
        self.refresh()

    def refresh(self):
        self.tv.delete(*self.tv.get_children())
        rows = db.get_verb_forms()
        for i, r in enumerate(rows):
            rname = ""
            if r["root_id"]:
                ri = db.get_root_by_id(r["root_id"])
                rname = ri["root"] if ri else ""
            tag = ("odd",) if i % 2 else ()
            self.tv.insert("", "end", iid=str(r["id"]),
                values=(r["infinitive"], r["present_stem"],
                        r["past_stem"], r["verb_class"], rname),
                tags=tag)
        self._count_lbl.config(text=f"{len(rows)} феъл")

    def _do_search(self):
        q = self._q.get().strip().lower()
        if not q:
            self.refresh(); return
        self.tv.delete(*self.tv.get_children())
        rows = [r for r in db.get_verb_forms()
                if q in str(r["infinitive"]).lower()
                or q in str(r["present_stem"]).lower()
                or q in str(r["past_stem"]).lower()]
        for i, r in enumerate(rows):
            rname = ""
            if r["root_id"]:
                ri = db.get_root_by_id(r["root_id"])
                rname = ri["root"] if ri else ""
            tag = ("odd",) if i % 2 else ()
            self.tv.insert("", "end", iid=str(r["id"]),
                values=(r["infinitive"], r["present_stem"],
                        r["past_stem"], r["verb_class"], rname),
                tags=tag)
        self._count_lbl.config(text=f"{len(rows)} феъл")

    def _open_add(self):
        dlg = tk.Toplevel(self)
        dlg.title("＋ Феъл илова кунед")
        dlg.geometry("360x140")
        dlg.configure(bg=BG)
        dlg.grab_set()
        dlg.resizable(False, False)

        grid = tk.Frame(dlg, bg=BG)
        grid.pack(fill="x", padx=18, pady=(18, 8))
        grid.columnconfigure(1, weight=1)

        _lbl(grid, "Масдар:").grid(row=0, column=0, sticky="e", padx=(0, 8), pady=6)
        e_inf = _entry(grid, 28)
        e_inf.grid(row=0, column=1, sticky="ew", pady=6)

        msg = _lbl(dlg, "", fg=RED)
        msg.pack(pady=(0, 4))

        def _save():
            inf = e_inf.get().strip()
            if not inf:
                msg.config(text="⚠  Масдар холӣ!"); return
            r = db.add_verb_form(inf, "", "", "", "")
            if r == "exists":
                msg.config(text="⚠  Ин феъл аллакай мавҷуд аст!"); return
            self.refresh()
            dlg.destroy()

        bf = _fr(dlg)
        bf.pack(pady=(0, 12))
        _btn(bf, "✔ Захира", _save,       "Acc.TButton").pack(side="left", padx=6)
        _btn(bf, "Бекор",    dlg.destroy, "Std.TButton").pack(side="left", padx=6)

        e_inf.bind("<Return>", lambda _: _save())
        e_inf.focus_set()

    def _delete(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showwarning("Хато", "Феъл интихоб кунед!"); return
        v = self.tv.item(sel[0], "values")
        if messagebox.askyesno("Ҳазф", f"«{v[0]}» ҳазф карда шавад?"):
            db.delete_verb_form(int(sel[0]))
            self.refresh()


# ══════════════════════════════════════════════════════════════════════════════
# Сермаъноӣ
# ══════════════════════════════════════════════════════════════════════════════
class PolysemyTab(tk.Frame):
    def __init__(self, nb):
        super().__init__(nb, bg=BG)
        self._build()

    def _build(self):
        # ── ҷустуҷӯ ────────────────────────────────────────────────────────
        sf = _fr(self)
        sf.pack(fill="x", padx=12, pady=(10, 4))

        _lbl(sf, "Ҷустуҷӯ:").pack(side="left")
        self._search = _entry(sf, 22)
        self._search.pack(side="left", padx=(4, 8))
        self._search.bind("<Return>",    lambda e: self._do_search())
        self._search.bind("<KeyRelease>",lambda e: self._do_search())

        _btn(sf, "＋ Илова", self._open_add, "Acc.TButton").pack(side="left", padx=2)
        _btn(sf, "⟳ Ҳама",  self.refresh,   "Std.TButton").pack(side="left", padx=2)
        _btn(sf, "✕ Ҳазф",  self._delete,   "Del.TButton").pack(side="left", padx=6)

        self._count_lbl = _lbl(sf, "", fg=FG2)
        self._count_lbl.pack(side="right", padx=8)

        # ── ҷадвал ─────────────────────────────────────────────────────────
        tf = _fr(self)
        tf.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.tv = _tree(tf, ["Калима","№","Ҷузъи нутқ","Соҳа","Маъно","Мисол"],
                        [130, 36, 90, 90, 220, 200], height=22)
        self.tv.tag_configure("odd", background=BG4)
        self.refresh()

    def refresh(self):
        self.tv.delete(*self.tv.get_children())
        rows = db.get_polysemy()
        for i, r in enumerate(rows):
            tag = ("odd",) if i % 2 else ()
            self.tv.insert("", "end", iid=str(r["id"]),
                values=(r["word"], r["meaning_num"], r["pos"],
                        r["domain"], r["meaning"], r["example"]),
                tags=tag)
        self._count_lbl.config(text=f"{len(rows)} маъно")

    def _do_search(self):
        q = self._search.get().strip()
        if not q:
            self.refresh(); return
        self.tv.delete(*self.tv.get_children())
        rows = db.search_polysemy(q)
        for i, r in enumerate(rows):
            tag = ("odd",) if i % 2 else ()
            self.tv.insert("", "end", iid=str(r["id"]),
                values=(r["word"], r["meaning_num"], r["pos"],
                        r["domain"], r["meaning"], r["example"]),
                tags=tag)
        self._count_lbl.config(text=f"{len(rows)} маъно")

    def _open_add(self):
        dlg = tk.Toplevel(self)
        dlg.title("＋ Калима илова кунед")
        dlg.geometry("360x140")
        dlg.configure(bg=BG)
        dlg.grab_set()
        dlg.resizable(False, False)

        grid = tk.Frame(dlg, bg=BG)
        grid.pack(fill="x", padx=18, pady=(18, 8))
        grid.columnconfigure(1, weight=1)

        _lbl(grid, "Калима:").grid(row=0, column=0, sticky="e", padx=(0, 8), pady=6)
        e_word = _entry(grid, 28)
        e_word.grid(row=0, column=1, sticky="ew", pady=6)

        msg = _lbl(dlg, "", fg=RED)
        msg.pack(pady=(0, 4))

        def _save():
            word = e_word.get().strip()
            if not word:
                msg.config(text="⚠  Калима холӣ!"); return
            r = db.add_polysemy(word, 0, "", "", "", "")
            if r == "exists":
                msg.config(text="⚠  Ин калима аллакай мавҷуд аст!"); return
            self.refresh()
            dlg.destroy()

        bf = _fr(dlg)
        bf.pack(pady=(0, 12))
        _btn(bf, "✔ Захира", _save,       "Acc.TButton").pack(side="left", padx=6)
        _btn(bf, "Бекор",    dlg.destroy, "Std.TButton").pack(side="left", padx=6)

        e_word.bind("<Return>", lambda _: _save())
        e_word.focus_set()

    def _delete(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showwarning("Хато", "Маъноро интихоб кунед!"); return
        v = self.tv.item(sel[0], "values")
        if messagebox.askyesno("Ҳазф",
                f"Маъно №{v[1]} барои «{v[0]}» ҳазф шавад?"):
            db.delete_polysemy(int(sel[0]))
            self.refresh()


# ══════════════════════════════════════════════════════════════════════════════
# Таҳлили морфологӣ + тарҷумаи автоматӣ + AI
# ══════════════════════════════════════════════════════════════════════════════
import os as _os
_API_KEY_FILE = _os.path.join(_os.path.dirname(__file__), ".api_key")


def _load_api_key() -> str:
    if _os.path.exists(_API_KEY_FILE):
        with open(_API_KEY_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return _os.environ.get("ANTHROPIC_API_KEY", "")


def _save_api_key(key: str):
    with open(_API_KEY_FILE, "w", encoding="utf-8") as f:
        f.write(key.strip())


class MorphTab(tk.Frame):
    """Таҳлили морфологӣ · Тарҷумаи автоматӣ · AI-таҳлил"""

    def __init__(self, nb):
        super().__init__(nb, bg=BG)
        self._api_key = _load_api_key()
        self._build()

    # ── сохтор ─────────────────────────────────────────────────────────────
    def _build(self):
        # ══ Сатри вуруд ══════════════════════════════════════════════════
        top = _fr(self)
        top.pack(fill="x", padx=14, pady=(14, 4))

        _lbl(top, "Матн (калима ё ҷумла):").grid(row=0, column=0, sticky="w", padx=(0,6))
        self._inp = ttk.Entry(top, width=52, font=("Segoe UI", 11))
        self._inp.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        top.columnconfigure(1, weight=1)
        self._inp.bind("<Return>", lambda _: self._run_all())

        _btn(top, "🔬 Таҳлил",  self._run_all, "Acc.TButton").grid(row=0, column=2, padx=2)
        _btn(top, "✕ Тоза",    self._clear,   "Std.TButton").grid(row=0, column=3, padx=2)

        # ── калиди API ──────────────────────────────────────────────────
        kf = _fr(self)
        kf.pack(fill="x", padx=14, pady=(2, 6))

        _lbl(kf, "API калид:").pack(side="left")
        self._key_var = tk.StringVar(value=self._api_key)
        key_e = ttk.Entry(kf, textvariable=self._key_var, width=40,
                          show="•", font=("Consolas", 9))
        key_e.pack(side="left", padx=(4, 6))
        _btn(kf, "Нигоҳ", self._save_key, "Std.TButton").pack(side="left")
        self._key_msg = _lbl(kf, "", fg=GRN)
        self._key_msg.pack(side="left", padx=6)

        _lbl(kf, "А=адабӣ  Л=лаҳҷавӣ  ?=нест", fg=FG2).pack(side="right", padx=8)

        tk.Frame(self, bg=BRD, height=1).pack(fill="x")

        # ══ Бадани асосӣ (PanedWindow) ═══════════════════════════════════
        pw = tk.PanedWindow(self, orient="vertical", bg=BG,
                            sashrelief="flat", sashwidth=4,
                            handlesize=0)
        pw.pack(fill="both", expand=True, padx=0, pady=0)

        # ── Блоки 1: Морфемаҳо + Тарҷума ─────────────────────────────
        top_pane = _fr(pw)

        # Морфемаҳо
        morph_hdr = _fr(top_pane)
        morph_hdr.pack(fill="x", padx=14, pady=(10, 4))
        _lbl(morph_hdr, "▸ Таҳлили морфологӣ", fg=ACC,
             font=("Segoe UI", 10, "bold")).pack(side="left")

        mf = _fr2(top_pane)
        mf.pack(fill="x", padx=14, pady=(0, 6))
        mf.configure(highlightbackground=BRD, highlightthickness=1)

        self._morph_frame = tk.Frame(mf, bg=BG2)
        self._morph_frame.pack(fill="x", padx=16, pady=(12, 8))

        tk.Frame(mf, bg=BRD, height=1).pack(fill="x", padx=12)

        df = tk.Frame(mf, bg=BG2)
        df.pack(fill="x", padx=16, pady=(8, 12))
        self._dv = {}
        for i, lbl in enumerate(["Пешванд:", "Реша:", "Пасванд:", "Адабии шакл:"]):
            tk.Label(df, text=lbl, bg=BG2, fg=FG2, font=FN,
                     anchor="e", width=15).grid(row=i, column=0, sticky="e",
                                                pady=3, padx=(0, 10))
            v = tk.Label(df, text="—", bg=BG2, fg=FG, font=FN, anchor="w")
            v.grid(row=i, column=1, sticky="w", pady=3)
            self._dv[lbl] = v

        # Тарҷума
        trans_hdr = _fr(top_pane)
        trans_hdr.pack(fill="x", padx=14, pady=(6, 4))
        _lbl(trans_hdr, "▸ Тарҷумаи автоматӣ ба адабӣ", fg=ACC,
             font=("Segoe UI", 10, "bold")).pack(side="left")
        self._trans_stat = _lbl(trans_hdr, "", fg=FG2)
        self._trans_stat.pack(side="left", padx=10)

        tf_wrap = _fr2(top_pane)
        tf_wrap.pack(fill="x", padx=14, pady=(0, 8))
        tf_wrap.configure(highlightbackground=BRD, highlightthickness=1)

        # Ду сатр: лаҳҷавӣ ва адабӣ бо рангбандӣ
        self._trans_canvas_frame = tk.Frame(tf_wrap, bg=BG2)
        self._trans_canvas_frame.pack(fill="x", padx=12, pady=10)

        pw.add(top_pane, stretch="always", minsize=220)

        # ── Блоки 2: AI-таҳлил ────────────────────────────────────────
        ai_pane = _fr(pw)

        ai_hdr = _fr(ai_pane)
        ai_hdr.pack(fill="x", padx=14, pady=(10, 4))
        _lbl(ai_hdr, "▸ Таҳлили Claude AI — дар кадом ноҳияҳо истифода мебаранд",
             fg=ACC, font=("Segoe UI", 10, "bold")).pack(side="left")
        _btn(ai_hdr, "🤖 AI Таҳлил", self._run_ai, "Acc.TButton").pack(side="left", padx=10)
        self._ai_status = _lbl(ai_hdr, "", fg=YLW)
        self._ai_status.pack(side="left")

        ai_wrap = tk.Frame(ai_pane, bg=BG2,
                           highlightbackground=BRD, highlightthickness=1)
        ai_wrap.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        self._ai_text = tk.Text(ai_wrap, bg=BG2, fg=FG, font=FN,
                                relief="flat", insertbackground=FG,
                                wrap="word", padx=12, pady=10,
                                state="disabled")
        ai_sb = ttk.Scrollbar(ai_wrap, orient="vertical",
                              command=self._ai_text.yview)
        self._ai_text.configure(yscrollcommand=ai_sb.set)
        self._ai_text.pack(side="left", fill="both", expand=True)
        ai_sb.pack(side="right", fill="y")

        pw.add(ai_pane, stretch="always", minsize=160)

    # ── Ёрдамчиҳо ──────────────────────────────────────────────────────────
    def _morph_box(self, parent, text, is_dialectal, found=True, kind=""):
        if not text:
            return
        if not found:
            fg, bg_c, badge = RED, "#2d1a1a", "?"
        elif is_dialectal:
            fg, bg_c, badge = YLW, "#2d2500", "Л"
        else:
            fg, bg_c, badge = GRN, "#0d2010", "А"
        col = tk.Frame(parent, bg=BG2)
        col.pack(side="left", padx=6, pady=2)
        tk.Label(col, text=kind, bg=BG2, fg=FG2, font=("Segoe UI", 8)).pack()
        box = tk.Frame(col, bg=bg_c, padx=10, pady=6,
                       highlightbackground=fg, highlightthickness=1)
        box.pack()
        tk.Label(box, text=text, bg=bg_c, fg=fg,
                 font=("Segoe UI", 15, "bold")).pack()
        tk.Label(col, text=badge, bg=BG2, fg=fg,
                 font=("Segoe UI", 8, "bold")).pack()

    def _set_text(self, widget, content, state="disabled"):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", content)
        widget.config(state=state)

    def _save_key(self):
        k = self._key_var.get().strip()
        if k:
            self._api_key = k
            _save_api_key(k)
            self._key_msg.config(text="✔ Захира шуд", fg=GRN)
            self.after(2000, lambda: self._key_msg.config(text=""))
        else:
            self._key_msg.config(text="⚠ Холӣ", fg=YLW)

    def _clear(self):
        self._inp.delete(0, "end")
        for w in self._morph_frame.winfo_children():
            w.destroy()
        for v in self._dv.values():
            v.config(text="—", fg=FG)
        for w in self._trans_canvas_frame.winfo_children():
            w.destroy()
        self._trans_stat.config(text="")
        self._set_text(self._ai_text, "")
        self._ai_status.config(text="")

    # ── Таҳлили асосӣ ──────────────────────────────────────────────────────
    def _run_all(self):
        text = self._inp.get().strip()
        if not text:
            return
        words = text.split()

        # Морфемаҳо — барои калимаи аввал (ё ягона)
        self._do_morph(words[0] if words else text)

        # Тарҷумаи ҷумла
        self._do_translate(text)

    def _do_morph(self, word):
        res  = db.morph_analyze_word(word)
        pref = res["prefix"]
        root = res["root"]
        suf  = res["suffix"]

        for w in self._morph_frame.winfo_children():
            w.destroy()

        if pref["form"]:
            self._morph_box(self._morph_frame, pref["form"],
                            pref["is_dialectal"], True, "Пешванд")
        self._morph_box(self._morph_frame, root["form"] or word,
                        root["is_dialectal"], root["found"], "Реша")
        if suf["form"]:
            self._morph_box(self._morph_frame, suf["form"],
                            suf["is_dialectal"], True, "Пасванд")

        def _fmt_pref():
            if not pref["form"]: return "—"
            t = pref["form"]
            if pref["is_dialectal"] and pref["literary"] != pref["form"]:
                t += f"  →  адабӣ: «{pref['literary']}»"
            return t

        def _fmt_root():
            t = root["form"] or "—"
            if root["is_dialectal"] and root["literary"] and root["literary"] != root["form"]:
                t += f"  →  адабӣ: «{root['literary']}»"
            t += "  ✓" if root["found"] else "  ✗ (дар база нест)"
            return t

        def _fmt_suf():
            if not suf["form"]: return "—"
            t = suf["form"]
            if suf["is_dialectal"] and suf["literary"] and suf["literary"] != suf["form"]:
                t += f"  →  адабӣ: «{suf['literary']}»"
            if suf["meaning"]:
                t += f"  [{suf['meaning']}]"
            return t

        self._dv["Пешванд:"].config(
            text=_fmt_pref(),
            fg=YLW if pref["is_dialectal"] else (FG if pref["form"] else FG2))
        self._dv["Реша:"].config(
            text=_fmt_root(),
            fg=YLW if root["is_dialectal"] else (GRN if root["found"] else RED))
        self._dv["Пасванд:"].config(
            text=_fmt_suf(),
            fg=YLW if suf["is_dialectal"] else (FG if suf["form"] else FG2))
        self._dv["Адабии шакл:"].config(
            text=res["literary_reconstruction"] or "—", fg=ACC)

    def _do_translate(self, text):
        res = db.phrase_to_literary(text)

        for w in self._trans_canvas_frame.winfo_children():
            w.destroy()

        # Сатри 1: лаҳҷавӣ (асл) — ҳар токен бо рангбандӣ
        row1 = tk.Frame(self._trans_canvas_frame, bg=BG2)
        row1.pack(fill="x", pady=(0, 4))
        _lbl(row1, "Лаҳҷа: ", fg=FG2, bg=BG2).pack(side="left")
        for tok in res["tokens"]:
            fg = YLW if tok["changed"] else FG
            tk.Label(row1, text=tok["original"], bg=BG2, fg=fg,
                     font=FN).pack(side="left")

        # Сатри 2: адабӣ
        row2 = tk.Frame(self._trans_canvas_frame, bg=BG2)
        row2.pack(fill="x")
        _lbl(row2, "Адабӣ:  ", fg=FG2, bg=BG2).pack(side="left")
        for tok in res["tokens"]:
            fg = GRN if tok["changed"] else FG
            tk.Label(row2, text=tok["literary"], bg=BG2, fg=fg,
                     font=FN).pack(side="left")

        ch = res["changed"]
        total = sum(1 for t in res["tokens"] if t["original"].strip())
        self._trans_stat.config(
            text=f"({ch} аз {total} калима тағйир ёфт)" if ch else "(тағйир нашуд)")

    # ── AI-таҳлил ──────────────────────────────────────────────────────────
    def _run_ai(self):
        text = self._inp.get().strip()
        if not text:
            return

        # API калидро аз майдони вуруд тоза гирем
        key = self._key_var.get().strip() or self._api_key
        if not key:
            self._set_text(self._ai_text,
                "⚠  Калиди API дохил кунед (сатри «API калид» дар боло).")
            return

        self._api_key = key

        # lit_words аз тарҷума
        trans = db.phrase_to_literary(text)
        lit_words = trans["lit_words"] or None

        self._ai_status.config(text="⏳ Дар ҳоли таҳлил…")
        self._set_text(self._ai_text, "")

        import ai_analyzer

        def _on_result(txt):
            self._ai_status.config(text="✔ Тамом")
            self._set_text(self._ai_text, txt)

        def _on_error(msg):
            self._ai_status.config(text="✗ Хато")
            self._set_text(self._ai_text, f"Хато: {msg}")

        ai_analyzer.analyze_dialect(text, key, _on_result, _on_error,
                                    lit_words=lit_words)


# ══════════════════════════════════════════════════════════════════════════════
# Мӯҳтавои асосӣ
# ══════════════════════════════════════════════════════════════════════════════
def _build_content(win: tk.BaseWidget):
    _apply_style()
    db.init_db()
    win.configure(bg=BG)

    # Header
    hf = tk.Frame(win, bg=BG)
    hf.pack(fill="x", padx=16, pady=(12, 6))
    tk.Label(hf, text="📚  Луғатхона", font=FH,
             bg=BG, fg=ACC).pack(side="left")
    tk.Label(hf, text="— идоракунии маълумоти луғавӣ",
             font=FN, bg=BG, fg=FG2).pack(side="left", padx=8)

    # Separator
    tk.Frame(win, bg=BRD, height=1).pack(fill="x", padx=0)

    # Notebook
    nb = ttk.Notebook(win, )
    nb.pack(fill="both", expand=True, padx=0, pady=0)

    tabs = [
        (WordsTab,    "  Калимаҳо  "),
        (RootsTab,    "  Решаҳо  "),
        (PrefixesTab, "  Пешвандҳо  "),
        (SuffixesTab, "  Пасвандҳо  "),
        (VerbsTab,    "  Феълҳо  "),
        (PolysemyTab, "  Сермаъноӣ  "),
        (MorphTab,    "  🔬 Таҳлили морфологӣ  "),
    ]
    for cls, label in tabs:
        tab = cls(nb)
        nb.add(tab, text=label)

    # Status bar
    sb = tk.Frame(win, bg=BG3, height=26)
    sb.pack(fill="x", side="bottom")
    tk.Label(sb, text="Омода", bg=BG3, fg=FG2,
             font=("Segoe UI", 9), anchor="w", padx=10).pack(fill="x", pady=4)


# ══════════════════════════════════════════════════════════════════════════════
# Оғозгарҳо
# ══════════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Луғатхона — Идоракунии маълумоти луғавӣ")
        self.geometry("1160x800")
        _build_content(self)


def open_as_toplevel(master: tk.BaseWidget) -> tk.Toplevel:
    win = tk.Toplevel(master)
    win.title("Луғатхона — Идоракунии маълумоти луғавӣ")
    win.geometry("1100x720")
    win.grab_set()
    _build_content(win)
    win.transient(master)
    return win


def main():
    App().mainloop()


if __name__ == "__main__":
    main()


