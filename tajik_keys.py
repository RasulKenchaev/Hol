import tkinter as tk
from tkinter import ttk

# ц→қ  ы→ҷ  ь→ӣ  щ→ҳ  -→ғ  =→ӯ
TAJIK_REMAP = {
    "ц": "қ",  "Ц": "Қ",
    "ы": "ҷ",  "Ы": "Ҷ",
    "ь": "ӣ",  "Ь": "Ӣ",
    "щ": "ҳ",  "Щ": "Ҳ",
    "-": "ғ",
    "=": "ӯ",
}
TAJIK_KEYCODE = {
    87:  ("қ", "Қ"),   # W / ц
    83:  ("ҷ", "Ҷ"),   # S / ы
    77:  ("ӣ", "Ӣ"),   # M / ь
    79:  ("ҳ", "Ҳ"),   # O / щ
    189: ("ғ", "Ғ"),   # -
    187: ("ӯ", "Ӯ"),   # =
}

_TAG = "TajikKeymap"
_setup_done = False


def setup(root):
    """
    Як бор фарохонда мешавад.
    bind_class барои тегги _TAG сабт мекунад — пеш аз класс-бандинг иҷро мешавад.
    """
    global _setup_done
    if _setup_done:
        return
    _setup_done = True

    def _on_key(event):
        if event.state & 0x4:   # Ctrl — гузаред
            return
        mapped = TAJIK_REMAP.get(event.char)
        if not mapped:
            pair = TAJIK_KEYCODE.get(event.keycode)
            if pair:
                mapped = pair[1] if (event.state & 0x1) else pair[0]
        if not mapped:
            return
        w = event.widget
        try:
            if isinstance(w, tk.Text):
                try:
                    w.delete("sel.first", "sel.last")
                except tk.TclError:
                    pass
                w.insert(tk.INSERT, mapped)
            else:
                try:
                    w.delete(w.index("sel.first"), w.index("sel.last"))
                except tk.TclError:
                    pass
                w.insert(w.index(tk.INSERT), mapped)
        except tk.TclError:
            return           # widget навишта нашавад — default-ро иҷоза медиҳем
        return "break"       # default class-binding иҷро нашавад

    root.bind_class(_TAG, "<KeyPress>", _on_key)


def apply_tajik_keys(widget):
    """
    Теги TajikKeymap-ро ДАР ПЕШИ класс-тег дар bindtags мегузорад.
    Ин кафолат медиҳад, ки handler-и мо пеш аз insertion-и дефолт иҷро шавад.
    """
    tags = list(widget.bindtags())
    if _TAG in tags:
        return                          # аллакай татбиқ шудааст
    cls = widget.winfo_class()          # "Text", "Entry", "TEntry" …
    idx = tags.index(cls) if cls in tags else 1
    tags.insert(idx, _TAG)
    widget.bindtags(tags)


def walk_and_bind(parent):
    """Ҳамаи Entry / Text-ҳои зерро пайдо карда apply_tajik_keys мезанад."""
    for child in parent.winfo_children():
        if isinstance(child, (tk.Text, tk.Entry, ttk.Entry)):
            apply_tajik_keys(child)
        walk_and_bind(child)
