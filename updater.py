"""
Модули навсозии барнома.
Версияи нав аз URL-и танзимшуда боргузорӣ ва насб мешавад.
"""
import os, sys, json, threading, shutil, tempfile
import urllib.request
import tkinter as tk
from tkinter import ttk, messagebox

_DIR          = os.path.dirname(os.path.abspath(__file__))
_VERSION_FILE = os.path.join(_DIR, "version.json")
_CFG_FILE     = os.path.join(_DIR, ".update_config")

_FILES = [
    "app.py", "db.py", "importer.py",
    "ai_analyzer.py", "offline_analyzer.py",
    "manage_linguistic.py", "tajik_keys.py",
    "updater.py",
]

# ── Ёрдамчиҳо ─────────────────────────────────────────────────────────────

def _local_version():
    try:
        with open(_VERSION_FILE, encoding="utf-8") as f:
            return json.load(f).get("version", "1.0.0")
    except Exception:
        return "1.0.0"


def _load_cfg():
    try:
        with open(_CFG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cfg(d):
    with open(_CFG_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f)


def _fetch(url, timeout=10):
    req = urllib.request.Request(
        url, headers={"User-Agent": "TajikDialectApp/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _ver_tuple(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except Exception:
        return (0,)


# ── Асосии UI ──────────────────────────────────────────────────────────────

def check_and_update(parent):
    cfg      = _load_cfg()
    base_url = cfg.get("base_url", "").strip()
    if not base_url:
        _setup_url_dialog(parent)
    else:
        _show_update_dialog(parent, base_url)


# ── Танзими URL ────────────────────────────────────────────────────────────

def _setup_url_dialog(parent):
    BG, FG = "#1a2535", "#ecf0f1"
    dlg = tk.Toplevel(parent)
    dlg.title("Танзими навсозӣ")
    dlg.geometry("500x200")
    dlg.configure(bg=BG)
    dlg.grab_set()
    dlg.resizable(False, False)

    tk.Label(dlg, text="🔄  Танзими сервери навсозӣ",
             bg=BG, fg=FG, font=("Segoe UI", 11, "bold")).pack(pady=(18, 6))
    tk.Label(dlg,
             text="Суроғаи GitHub Raw ё серверро ворид кунед:",
             bg=BG, fg="#95a5a6", font=("Segoe UI", 9)).pack()

    var = tk.StringVar(value=_load_cfg().get("base_url", ""))
    e = tk.Entry(dlg, textvariable=var, width=54,
                 bg="#2c3e50", fg=FG, insertbackground=FG,
                 relief="flat", font=("Segoe UI", 9), bd=6)
    e.pack(padx=24, pady=(8, 2), fill="x")
    tk.Label(dlg,
             text="Мисол: https://raw.githubusercontent.com/user/repo/main/",
             bg=BG, fg="#5d6d7e", font=("Segoe UI", 7)).pack(anchor="w", padx=24)

    def _save():
        url = var.get().strip()
        if not url:
            return
        if not url.endswith("/"):
            url += "/"
        _save_cfg({"base_url": url})
        dlg.destroy()
        _show_update_dialog(parent, url)

    btn = tk.Button(dlg, text="✔  Сабт ва санҷиш", command=_save,
                    bg="#27ae60", fg="#fff", relief="raised", bd=3,
                    font=("Segoe UI", 9, "bold"), cursor="hand2",
                    padx=14, pady=5, highlightthickness=0,
                    activebackground="#1d8348", activeforeground="#fff")
    btn.pack(pady=12)
    btn.bind("<Enter>", lambda e: btn.config(bg="#1d8348"))
    btn.bind("<Leave>", lambda e: btn.config(bg="#27ae60"))
    e.focus()
    dlg.bind("<Return>", lambda e: _save())


# ── Асосии диалог навсозӣ ──────────────────────────────────────────────────

def _show_update_dialog(parent, base_url):
    BG     = "#0d1b2a"
    CARD   = "#1a2535"
    ACC    = "#2ecc71"
    WARN   = "#f39c12"
    ERR    = "#e74c3c"
    FG     = "#ecf0f1"
    MUTED  = "#7f8c8d"
    BAR_W  = 400

    local_v = _local_version()

    dlg = tk.Toplevel(parent)
    dlg.title("🔄  Навсозии барнома")
    dlg.geometry("480x300")
    dlg.configure(bg=BG)
    dlg.grab_set()
    dlg.resizable(False, False)

    # ── Сарлавҳа ────────────────────────────────────────────────────
    tk.Label(dlg, text="🔄  Навсозии барнома",
             bg=BG, fg=FG, font=("Segoe UI", 13, "bold")).pack(pady=(20, 2))
    tk.Label(dlg, text=f"Версияи ҷорӣ:  {local_v}",
             bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack()

    # ── Ҷузъи нав ───────────────────────────────────────────────────
    card = tk.Frame(dlg, bg=CARD, bd=0)
    card.pack(fill="x", padx=30, pady=12)

    new_lbl = tk.Label(card, text="Версияи нав:  —",
                       bg=CARD, fg=FG, font=("Segoe UI", 10))
    new_lbl.pack(pady=(10, 2))

    status_lbl = tk.Label(card, text="Санҷиши навсозӣ…",
                          bg=CARD, fg=WARN, font=("Segoe UI", 9))
    status_lbl.pack(pady=(0, 8))

    # ── Нишондиҳандаи пешравӣ ────────────────────────────────────────
    bar_bg = tk.Frame(dlg, bg="#1e3050", height=10, width=BAR_W)
    bar_bg.pack(pady=(0, 4))
    bar_bg.pack_propagate(False)
    bar_fill = tk.Frame(bar_bg, bg=ACC, height=10, width=0)
    bar_fill.place(x=0, y=0, height=10)

    pct_lbl = tk.Label(dlg, text="", bg=BG, fg=MUTED,
                       font=("Segoe UI", 8))
    pct_lbl.pack()

    # ── Тугма ────────────────────────────────────────────────────────
    action_btn = tk.Button(dlg, text="⬇  Насб кунед",
                           state="disabled",
                           bg="#117a65", fg="#fff",
                           relief="raised", bd=3,
                           font=("Segoe UI", 10, "bold"),
                           cursor="hand2", padx=18, pady=6,
                           highlightthickness=0,
                           activebackground="#0e6655",
                           activeforeground="#fff")
    action_btn.pack(pady=10)

    remote_ver = [None]

    def _ui(fn, *a):
        dlg.after(0, fn, *a)

    def _set_status(msg, color=MUTED):
        _ui(status_lbl.config, text=msg, fg=color)

    def _set_prog(pct):
        w = max(0, int(BAR_W * pct / 100))
        _ui(bar_fill.config, width=w)
        _ui(pct_lbl.config,  text=f"{pct}%")

    def _enable_btn(text, cmd, bg="#117a65"):
        def _do():
            action_btn.config(text=text, state="normal",
                              command=cmd, bg=bg,
                              activebackground=bg)
            action_btn.bind("<Enter>",
                lambda e, b=action_btn, c=bg:
                    b.config(bg=_darken(c)))
            action_btn.bind("<Leave>",
                lambda e, b=action_btn, c=bg:
                    b.config(bg=c))
            action_btn.bind("<ButtonPress-1>",
                lambda e, b=action_btn, c=bg:
                    b.config(relief="sunken", bg=_darken(c, .5)))
            action_btn.bind("<ButtonRelease-1>",
                lambda e, b=action_btn, c=bg:
                    b.config(relief="raised", bg=c))
        _ui(_do)

    # ── Санҷиши версия ───────────────────────────────────────────────
    def _check():
        try:
            data = _fetch(base_url + "version.json")
            info = json.loads(data.decode("utf-8"))
            rv   = info.get("version", "0.0.0")
            remote_ver[0] = rv
            _ui(new_lbl.config, text=f"Версияи нав:  {rv}")
            _set_prog(100)
            if _ver_tuple(rv) > _ver_tuple(local_v):
                _set_status(f"✓  Версияи {rv} мавҷуд аст!", ACC)
                _enable_btn("⬇  Насб кунед", _start_update)
            else:
                _set_status("✓  Барнома навтарин аст", ACC)
        except Exception as ex:
            _set_status(f"⚠  Хатогӣ: {ex}", ERR)

    # ── Боргузорӣ ва насб ───────────────────────────────────────────
    def _start_update():
        rv = remote_ver[0]
        if not rv:
            return
        _ui(action_btn.config, state="disabled")
        _set_status("Боргузорӣ…", WARN)
        _set_prog(0)

        def _do():
            try:
                tmp = tempfile.mkdtemp()
                n   = len(_FILES)
                for i, fn in enumerate(_FILES):
                    _set_status(f"Боргузорӣ: {fn}", WARN)
                    try:
                        data = _fetch(base_url + fn)
                        with open(os.path.join(tmp, fn), "wb") as f:
                            f.write(data)
                    except Exception:
                        pass
                    _set_prog(int((i + 1) / n * 85))

                _set_status("Насб…", WARN)
                for fn in _FILES:
                    src = os.path.join(tmp, fn)
                    dst = os.path.join(_DIR, fn)
                    if os.path.exists(src):
                        shutil.copy2(src, dst)
                _set_prog(95)

                with open(_VERSION_FILE, "w", encoding="utf-8") as f:
                    json.dump({"version": rv}, f)
                shutil.rmtree(tmp, ignore_errors=True)
                _set_prog(100)
                _set_status(f"✓  Версияи {rv} насб шуд!", ACC)
                _enable_btn("♻  Барнома дубора оғоз", _restart, "#117a65")

            except Exception as ex:
                _set_status(f"⚠  Хатогӣ: {ex}", ERR)
                _ui(action_btn.config, state="normal")

        threading.Thread(target=_do, daemon=True).start()

    def _restart():
        dlg.destroy()
        parent.after(300, lambda: os.execv(
            sys.executable, [sys.executable] + sys.argv))

    threading.Thread(target=_check, daemon=True).start()


def _darken(hex_col, factor=0.75):
    r = int(hex_col[1:3], 16)
    g = int(hex_col[3:5], 16)
    b = int(hex_col[5:7], 16)
    return (f"#{max(0,int(r*factor)):02x}"
            f"{max(0,int(g*factor)):02x}"
            f"{max(0,int(b*factor)):02x}")
