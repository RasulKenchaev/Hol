"""
Лаҳҷаҳои Тоҷикистон — Kivy/KivyMD
Android • macOS • Windows • Linux
"""
import os, sys, threading

# Android: маълумотҳоро дар storage нигоҳ медорем
_IS_ANDROID = "ANDROID_ARGUMENT" in os.environ
if _IS_ANDROID:
    from android.storage import app_storage_path      # type: ignore
    _DB_DIR = app_storage_path()
else:
    _DB_DIR = os.path.dirname(os.path.abspath(__file__))

os.environ.setdefault("KIVY_NO_ENV_CONFIG", "1")

import db
db._DB_PATH = os.path.join(_DB_DIR, "dialect.db")   # type: ignore
db.init_db()

import analyzer as anlz

from kivy.lang import Builder
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.properties import StringProperty

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.list import MDList, TwoLineListItem, IconRightWidget
from kivymd.uix.toolbar import MDTopAppBar

# ── Desktop андозаи тирезаи аввала ───────────────────────────────────────────
if not _IS_ANDROID:
    Window.size = (420, 720)

# ─────────────────────────────────────────────────────────────────────────────
KV = """
#:import dp kivy.metrics.dp

<RoundCard@MDCard>:
    radius: [dp(12)]
    elevation: 3
    padding: dp(12)
    md_bg_color: app.theme_cls.bg_dark

# ── Экрани вуруд ─────────────────────────────────────────────────────────────
<LoginScreen>:
    name: "login"
    MDBoxLayout:
        orientation: "vertical"
        md_bg_color: app.theme_cls.bg_darkest

        # Аксент хат
        Widget:
            size_hint_y: None
            height: dp(3)
            canvas:
                Color:
                    rgba: app.theme_cls.primary_color
                Rectangle:
                    size: self.size
                    pos:  self.pos

        Widget:
            size_hint_y: None
            height: dp(40)

        # Логотип
        MDBoxLayout:
            orientation: "horizontal"
            size_hint_y: None
            height: dp(60)
            spacing: dp(10)
            padding: [dp(30), 0]
            MDLabel:
                text: "тҶ"
                font_style: "H4"
                bold: True
                theme_text_color: "Custom"
                text_color: 0.93, 0.3, 0.2, 1
                size_hint_x: None
                width: dp(60)
            MDBoxLayout:
                orientation: "vertical"
                MDLabel:
                    text: "Лаҳҷаҳои Тоҷикистон"
                    font_style: "Subtitle1"
                    bold: True
                    theme_text_color: "Primary"
                MDLabel:
                    text: "Вуруд ба система"
                    font_style: "Caption"
                    theme_text_color: "Secondary"

        Widget:
            size_hint_y: None
            height: dp(20)

        MDSeparator:
            color: 0.2, 0.2, 0.2, 1

        Widget:
            size_hint_y: None
            height: dp(24)

        # Майдонҳо
        MDTextField:
            id: inp_user
            hint_text: "Логин"
            icon_left: "account"
            size_hint_x: None
            width: dp(280)
            pos_hint: {"center_x": .5}
            on_text_validate: root.on_enter_user()

        Widget:
            size_hint_y: None
            height: dp(8)

        MDTextField:
            id: inp_pass
            hint_text: "Парол"
            icon_left: "lock"
            password: True
            size_hint_x: None
            width: dp(280)
            pos_hint: {"center_x": .5}
            on_text_validate: root.do_login()

        Widget:
            size_hint_y: None
            height: dp(6)

        MDLabel:
            id: lbl_msg
            text: ""
            theme_text_color: "Custom"
            text_color: 0.94, 0.32, 0.3, 1
            halign: "center"
            size_hint_y: None
            height: dp(24)
            font_style: "Caption"

        Widget:
            size_hint_y: None
            height: dp(10)

        # Тугмаҳо
        MDBoxLayout:
            orientation: "horizontal"
            size_hint_x: None
            width: dp(280)
            pos_hint: {"center_x": .5}
            spacing: dp(12)
            MDRaisedButton:
                text: "➤  Вуруд"
                on_release: root.do_login()
                md_bg_color: app.theme_cls.primary_color
                size_hint_x: 1
            MDRaisedButton:
                text: "＋  Бақайдгирӣ"
                on_release: root.open_register()
                md_bg_color: 0.13, 0.15, 0.18, 1
                size_hint_x: 1

        Widget:

# ── Экрани асосӣ ──────────────────────────────────────────────────────────────
<MainScreen>:
    name: "main"
    MDBoxLayout:
        orientation: "vertical"

        # Тасмаи боло
        MDTopAppBar:
            id: toolbar
            title: "Лаҳҷаҳои Тоҷикистон"
            right_action_items:
                [["magnify", lambda x: root.tab_analysis()],
                 ["format-list-bulleted", lambda x: root.tab_dialects()],
                 ["cog", lambda x: root.tab_settings()]]
            md_bg_color: 0.05, 0.07, 0.1, 1

        MDScreenManager:
            id: tab_mgr
            AnalysisTab:
            DialectsTab:
            SettingsTab:

        # Таби поёнӣ
        MDBottomNavigation:
            id: bnav
            panel_color: 0.08, 0.10, 0.14, 1
            selected_color_background: app.theme_cls.primary_color
            text_color_active: app.theme_cls.primary_color

            MDBottomNavigationItem:
                name: "tab_analysis"
                text: "Таҳлил"
                icon: "text-search"
                on_tab_press: root.tab_analysis()

            MDBottomNavigationItem:
                name: "tab_dialects"
                text: "Ноҳияҳо"
                icon: "map-marker-multiple"
                on_tab_press: root.tab_dialects()

            MDBottomNavigationItem:
                name: "tab_settings"
                text: "Танзимот"
                icon: "cog-outline"
                on_tab_press: root.tab_settings()

# ── Таби таҳлил ──────────────────────────────────────────────────────────────
<AnalysisTab>:
    name: "analysis"
    MDBoxLayout:
        orientation: "vertical"
        padding: dp(10)
        spacing: dp(6)
        md_bg_color: app.theme_cls.bg_darkest

        # Матн
        MDTextField:
            id: inp_text
            hint_text: "Матни тоҷикиро ворид кунед…"
            mode: "rectangle"
            multiline: True
            size_hint_y: None
            height: dp(110)

        MDLabel:
            id: voice_status
            text: ""
            font_style: "Caption"
            theme_text_color: "Custom"
            text_color: 0.26, 0.65, 1, 1
            halign: "center"
            size_hint_y: None
            height: dp(18)

        # Тугмаҳо
        MDBoxLayout:
            size_hint_y: None
            height: dp(44)
            spacing: dp(8)
            MDRaisedButton:
                text: "🔍  Таҳлил"
                md_bg_color: app.theme_cls.primary_color
                on_release: root.analyze()
                size_hint_x: 2
            MDRaisedButton:
                id: mic_btn
                text: "🎤"
                md_bg_color: 0.15, 0.45, 0.85, 1
                on_release: root.start_voice()
                size_hint_x: None
                width: dp(50)
            MDRaisedButton:
                text: "✕  Тоза"
                md_bg_color: 0.55, 0.1, 0.1, 1
                on_release: root.clear_all()
                size_hint_x: 1

        # Беҳтарин лаҳҷа
        MDCard:
            id: card_best
            size_hint_y: None
            height: dp(54)
            radius: [dp(8)]
            md_bg_color: 0.08, 0.14, 0.22, 1
            padding: dp(10)
            opacity: 0
            MDBoxLayout:
                orientation: "vertical"
                MDLabel:
                    id: lbl_best
                    text: ""
                    font_style: "Subtitle1"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: app.theme_cls.primary_color
                MDLabel:
                    id: lbl_best_pct
                    text: ""
                    font_style: "Caption"
                    theme_text_color: "Secondary"

        # Матни рангин
        MDScrollView:
            size_hint_y: 1
            MDLabel:
                id: lbl_result
                text: "[color=888888]Матнро ворид кунед ва «Таҳлил»-ро пахш кунед…[/color]"
                markup: True
                font_size: dp(15)
                size_hint_y: None
                height: self.texture_size[1]
                text_size: self.width, None
                padding: [dp(4), dp(4)]
                valign: "top"
                theme_text_color: "Custom"
                text_color: 0.88, 0.88, 0.88, 1

        # Хулоса-лаҳҷаҳо
        MDScrollView:
            size_hint_y: None
            height: dp(90)
            MDBoxLayout:
                id: scores_row
                orientation: "horizontal"
                size_hint_x: None
                width: self.minimum_width
                spacing: dp(6)
                padding: [dp(2), dp(4)]

# ── Таби ноҳияҳо ─────────────────────────────────────────────────────────────
<DialectsTab>:
    name: "dialects"
    MDBoxLayout:
        orientation: "vertical"
        md_bg_color: app.theme_cls.bg_darkest

        # Тасмаи болоии амал
        MDBoxLayout:
            size_hint_y: None
            height: dp(52)
            padding: [dp(10), dp(6)]
            spacing: dp(8)
            md_bg_color: 0.08, 0.10, 0.14, 1

            MDTextField:
                id: search_field
                hint_text: "Ҷустуҷӯ…"
                size_hint_x: 1
                on_text: root.refresh(self.text)

            MDRaisedButton:
                text: "＋"
                size_hint_x: None
                width: dp(44)
                md_bg_color: 0.1, 0.47, 0.24, 1
                on_release: root.open_add_dialog()

        MDLabel:
            id: cnt_lbl
            text: ""
            font_style: "Caption"
            theme_text_color: "Secondary"
            size_hint_y: None
            height: dp(20)
            padding: [dp(12), 0]

        MDScrollView:
            MDList:
                id: dialect_list

# ── Таби танзимот ─────────────────────────────────────────────────────────────
<SettingsTab>:
    name: "settings"
    MDScrollView:
        MDBoxLayout:
            orientation: "vertical"
            padding: dp(16)
            spacing: dp(14)
            size_hint_y: None
            height: self.minimum_height
            md_bg_color: app.theme_cls.bg_darkest

            MDLabel:
                text: "Танзимоти барнома"
                font_style: "H6"
                theme_text_color: "Primary"
                size_hint_y: None
                height: dp(36)

            MDSeparator:

            MDTextField:
                id: api_key_field
                hint_text: "Claude API Key"
                icon_left: "key"
                password: True

            MDTextField:
                id: update_url_field
                hint_text: "URL-и навсозӣ (GitHub Raw)"
                icon_left: "update"

            MDRaisedButton:
                text: "💾  Захира"
                md_bg_color: app.theme_cls.primary_color
                on_release: root.save_settings()
                size_hint_x: None
                width: dp(140)
                pos_hint: {"center_x": .5}

            Widget:
                size_hint_y: None
                height: dp(10)

            MDSeparator:

            MDLabel:
                text: "Дар бораи барнома"
                font_style: "Subtitle1"
                bold: True
                theme_text_color: "Secondary"
                size_hint_y: None
                height: dp(30)

            MDLabel:
                text: "Лаҳҷаҳои Тоҷикистон v1.0\\nAndroid • macOS • Windows"
                font_style: "Body2"
                theme_text_color: "Hint"
                size_hint_y: None
                height: dp(40)
"""

Builder.load_string(KV)

# ── Харитаи номи ҳарфҳо → ҳарфи тоҷикӣ ────────────────────────────────────
_CHAR_NAMES = {
    "қоф": "қ", "қаф": "қ", "qof": "қ", "qaf": "қ",
    "ҷим": "ҷ", "ҷем": "ҷ", "jim": "ҷ",
    "ии": "ӣ", "ии борик": "ӣ", "и борик": "ӣ",
    "ҳе": "ҳ", "ҳо": "ҳ",
    "ғайн": "ғ", "ғаин": "ғ", "ghayn": "ғ",
    "уу": "ӯ", "уу гурда": "ӯ", "у гурда": "ӯ",
    "це": "қ", "же": "ҷ", "ха": "ҳ", "хе": "ҳ",
}
_CYR_CORRECTIONS = [
    ("дж", "ҷ"), ("дз", "ҷ"),
    ("гх", "ғ"), ("гь", "ғ"),
    ("хх", "ҳ"),
]
_LAT2CYR = [
    ("gh", "ғ"), ("kh", "х"), ("sh", "ш"), ("ch", "ч"),
    ("zh", "ж"), ("ts", "тс"), ("yo", "ё"),
    ("ii", "ӣ"), ("uu", "ӯ"),
    ("a", "а"), ("b", "б"), ("d", "д"), ("e", "е"), ("f", "ф"),
    ("g", "г"), ("h", "ҳ"), ("i", "и"), ("j", "ҷ"), ("k", "к"),
    ("l", "л"), ("m", "м"), ("n", "н"), ("o", "о"), ("p", "п"),
    ("q", "қ"), ("r", "р"), ("s", "с"), ("t", "т"), ("u", "у"),
    ("v", "в"), ("w", "в"), ("x", "х"), ("y", "й"), ("z", "з"),
]

_VOICE_REQUEST = 1001  # Android Activity request code


def _to_cyrillic(text: str) -> str:
    cyr = sum(1 for c in text if "Ѐ" <= c <= "ӿ")
    lat = sum(1 for c in text if c.isalpha() and c.isascii())
    if cyr >= lat:
        return text
    result, tl, i = [], text.lower(), 0
    while i < len(tl):
        matched = False
        for ls, cc in _LAT2CYR:
            if tl[i:i + len(ls)] == ls:
                result.append(cc.upper() if text[i].isupper() else cc)
                i += len(ls); matched = True; break
        if not matched:
            result.append(text[i]); i += 1
    return "".join(result)


def _post_process_voice(text: str) -> str:
    t = text.strip()
    key = t.lower()
    if key in _CHAR_NAMES:
        return _CHAR_NAMES[key]
    t = _to_cyrillic(t)
    for wrong, right in _CYR_CORRECTIONS:
        t = t.replace(wrong, right)
    return t


# ─────────────────────────────────────────────────────────────────────────────
# Экранҳо
# ─────────────────────────────────────────────────────────────────────────────

class LoginScreen(MDScreen):

    def on_enter_user(self):
        self.ids.inp_pass.focus = True

    def do_login(self):
        u = self.ids.inp_user.text.strip()
        p = self.ids.inp_pass.text
        if not u or not p:
            self.ids.lbl_msg.text = "⚠  Логин ва паролро пур кунед"
            return
        res = db.verify_user(u, p)
        if res:
            app = MDApp.get_running_app()
            app.current_user = res
            db.log_access(res["id"], "login")
            app.root.current = "main"
        else:
            self.ids.lbl_msg.text = "⚠  Логин ё парол нодуруст"
            self.ids.inp_pass.text = ""

    def open_register(self):
        self._reg_dialog = MDDialog(
            title="Бақайдгирӣ",
            type="custom",
            content_cls=RegisterContent(),
            buttons=[
                MDFlatButton(text="Бекор",
                             on_release=lambda x: self._reg_dialog.dismiss()),
                MDRaisedButton(text="✔  Сабт",
                               md_bg_color=(0.1, 0.47, 0.24, 1),
                               on_release=lambda x: self._do_register()),
            ],
        )
        self._reg_dialog.open()

    def _do_register(self):
        c = self._reg_dialog.content_cls
        u = c.ids.ru.text.strip()
        p = c.ids.rp.text
        cf = c.ids.rc.text
        if not u or not p:
            c.ids.rmsg.text = "⚠  Ҳама майдонҳоро пур кунед"; return
        if len(p) < 4:
            c.ids.rmsg.text = "⚠  Парол ҳадди ақал 4 ҳарф"; return
        if p != cf:
            c.ids.rmsg.text = "⚠  Паролҳо мувофиқ нестанд"; return
        res = db.register_user(u, p)
        if res:
            app = MDApp.get_running_app()
            app.current_user = res
            db.log_access(res["id"], "login")
            self._reg_dialog.dismiss()
            app.root.current = "main"
        else:
            c.ids.rmsg.text = "⚠  Ин логин аллакай банд аст"


class RegisterContent(MDBoxLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.orientation = "vertical"
        self.spacing = dp(6)
        self.size_hint_y = None
        self.height = dp(200)
        self.adaptive_height = True

        for fid, hint, pw in [("ru", "Логин", False),
                               ("rp", "Парол", True),
                               ("rc", "Тасдиқи парол", True)]:
            tf = MDTextField(hint_text=hint, password=pw)
            tf.id_ = fid
            self.add_widget(tf)
            setattr(self, "_" + fid, tf)
        msg = MDLabel(text="", theme_text_color="Custom",
                      text_color=(0.94, 0.32, 0.3, 1),
                      font_style="Caption",
                      size_hint_y=None, height=dp(20))
        self.add_widget(msg)
        self._msg = msg

    def _get_ids(self):
        class _Ids:
            pass
        o = _Ids()
        o.ru   = self._ru
        o.rp   = self._rp
        o.rc   = self._rc
        o.rmsg = self._msg
        return o

    @property
    def ids(self):
        return self._get_ids()


class AnalysisTab(MDScreen):
    _last_result = None

    def analyze(self):
        text = self.ids.inp_text.text.strip()
        if not text:
            return
        result = anlz.analyze_text(text)
        self._last_result = result
        markup = anlz.build_markup(result["tokens"], result["wr_map"])
        self.ids.lbl_result.text = markup or "[color=888888]Ягон лаҳҷавии калима ёфт нашуд[/color]"

        if result["best"]:
            self.ids.card_best.opacity = 1
            self.ids.lbl_best.text     = f"🏆  {result['best_name']}"
            self.ids.lbl_best_pct.text = f"{result['best_pct']}% мувофиқат"
        else:
            self.ids.card_best.opacity = 0

        # Хулоса-рекор барои ҳар лаҳҷа
        row = self.ids.scores_row
        row.clear_widgets()
        total = result["total"]
        dm    = result["dialects_meta"]
        top   = sorted(result["scores"].items(), key=lambda x: -x[1])[:8]
        for dk, sc in top:
            name = dm.get(dk, {}).get("name", dk)
            pct  = round(sc / total * 100)
            card = MDCard(
                size_hint=(None, None),
                size=(dp(80), dp(72)),
                radius=[dp(8)],
                md_bg_color=(0.08, 0.14, 0.22, 1),
                padding=dp(6),
            )
            box = MDBoxLayout(orientation="vertical")
            box.add_widget(MDLabel(
                text=str(pct) + "%",
                font_style="H6",
                bold=True,
                halign="center",
                theme_text_color="Custom",
                text_color=(0.26, 0.65, 1, 1),
            ))
            box.add_widget(MDLabel(
                text=name,
                font_style="Caption",
                halign="center",
                theme_text_color="Secondary",
            ))
            card.add_widget(box)
            row.add_widget(card)

    def clear_all(self):
        self.ids.inp_text.text   = ""
        self.ids.lbl_result.text = "[color=888888]Матнро ворид кунед ва «Таҳлил»-ро пахш кунед…[/color]"
        self.ids.card_best.opacity = 0
        self.ids.scores_row.clear_widgets()
        self.ids.voice_status.text = ""

    # ── Вуруди овозӣ ─────────────────────────────────────────────────────────

    def start_voice(self):
        if _IS_ANDROID:
            self._start_android_voice()
        else:
            self._start_desktop_voice()

    def _set_mic_state(self, recording: bool):
        btn = self.ids.mic_btn
        if recording:
            btn.text = "🔴"
            btn.md_bg_color = (0.75, 0.1, 0.1, 1)
            self.ids.voice_status.text = "Гӯш мекунам…"
        else:
            btn.text = "🎤"
            btn.md_bg_color = (0.15, 0.45, 0.85, 1)
            self.ids.voice_status.text = ""

    def _insert_voice_text(self, text: str):
        text = _post_process_voice(text)
        cur = self.ids.inp_text.text.strip()
        self.ids.inp_text.text = (cur + " " + text).strip() if cur else text
        self.ids.voice_status.text = f"✔  «{text}»"

    # Android ─────────────────────────────────────────────────────────────────
    def _start_android_voice(self):
        try:
            from android.permissions import request_permissions, check_permission, Permission  # type: ignore
            if not check_permission(Permission.RECORD_AUDIO):
                request_permissions([Permission.RECORD_AUDIO],
                                    callback=lambda perms, grants: self._start_android_voice()
                                    if grants and grants[0] else None)
                return

            from jnius import autoclass  # type: ignore
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Intent         = autoclass("android.content.Intent")
            RI             = autoclass("android.speech.RecognizerIntent")

            intent = Intent(RI.ACTION_RECOGNIZE_SPEECH)
            intent.putExtra(RI.EXTRA_LANGUAGE_MODEL, RI.LANGUAGE_MODEL_FREE_FORM)
            intent.putExtra(RI.EXTRA_LANGUAGE, "tg-TJ")
            intent.putExtra(RI.EXTRA_LANGUAGE_PREFERENCE, "tg-TJ")
            intent.putExtra(RI.EXTRA_ONLY_RETURN_LANGUAGE_PREFERENCE, False)
            intent.putExtra(RI.EXTRA_PROMPT, "Гап занед…")
            intent.putExtra(RI.EXTRA_MAX_RESULTS, 1)
            PythonActivity.mActivity.startActivityForResult(intent, _VOICE_REQUEST)
            self._set_mic_state(True)
        except Exception as e:
            self.ids.voice_status.text = f"⚠  {e}"

    # Desktop ─────────────────────────────────────────────────────────────────
    def _start_desktop_voice(self):
        self._set_mic_state(True)

        def _listen():
            text = None
            try:
                import speech_recognition as sr
                r = sr.Recognizer()
                r.energy_threshold = 300
                r.dynamic_energy_threshold = True
                with sr.Microphone() as src:
                    r.adjust_for_ambient_noise(src, duration=0.4)
                    audio = r.listen(src, timeout=8, phrase_time_limit=15)

                # Whisper
                try:
                    from faster_whisper import WhisperModel  # type: ignore
                    if not hasattr(AnalysisTab, "_wmodel"):
                        AnalysisTab._wmodel = WhisperModel("tiny", device="cpu",
                                                           compute_type="int8")
                    import tempfile
                    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                    tmp.write(audio.get_wav_data(convert_rate=16000, convert_width=2))
                    tmp.close()
                    segs, _ = AnalysisTab._wmodel.transcribe(tmp.name, language="tg", beam_size=5)
                    text = " ".join(s.text.strip() for s in segs).strip()
                    os.unlink(tmp.name)
                except Exception:
                    pass

                # Google fallback
                if not text:
                    for lang in ("tg-TJ", "ru-RU"):
                        try:
                            text = r.recognize_google(audio, language=lang); break
                        except Exception:
                            continue
            except Exception:
                pass

            def _done():
                self._set_mic_state(False)
                if text:
                    self._insert_voice_text(text)
                else:
                    self.ids.voice_status.text = "⚠  Ҳеҷ чиз нашунидам"
            Clock.schedule_once(lambda dt: _done(), 0)

        threading.Thread(target=_listen, daemon=True).start()


class DialectsTab(MDScreen):

    def on_enter(self):
        self.refresh()

    def refresh(self, query=""):
        lst = self.ids.dialect_list
        lst.clear_widgets()
        s2    = db.stats()
        pd_   = {r["name"]: r["cnt"] for r in s2.get("per_dialect", [])}
        items = db.get_dialects()
        q     = query.strip().lower() if query else ""
        shown = 0
        for d in items:
            if q and q not in d["name"].lower() and q not in d["key"].lower():
                continue
            cnt  = pd_.get(d["name"], 0)
            icon = IconRightWidget(icon="delete",
                                   theme_icon_color="Custom",
                                   icon_color=(0.9, 0.2, 0.2, 1))
            key_cap = d["key"]
            icon.bind(on_release=lambda _, k=key_cap: self._delete(k))
            item = TwoLineListItem(
                text=d["name"],
                secondary_text=f"{d.get('region','—')}   •   {cnt:,} калима",
            )
            item.add_widget(icon)
            lst.add_widget(item)
            shown += 1
        self.ids.cnt_lbl.text = f"  {shown} ноҳия"

    def open_add_dialog(self):
        self._add_field = MDTextField(hint_text="Номи ноҳия")
        self._add_dlg   = MDDialog(
            title="＋  Ноҳияи нав",
            type="custom",
            content_cls=self._add_field,
            buttons=[
                MDFlatButton(text="Бекор",
                             on_release=lambda x: self._add_dlg.dismiss()),
                MDRaisedButton(text="✔  Илова",
                               md_bg_color=(0.1, 0.47, 0.24, 1),
                               on_release=lambda x: self._do_add()),
            ],
        )
        self._add_dlg.open()

    def _do_add(self):
        nom = self._add_field.text.strip()
        if not nom:
            return
        key = nom.lower().replace(" ", "_")[:20]
        if db.add_dialect(key, nom, "", 0):
            self._add_dlg.dismiss()
            self.refresh()
            Snackbar(text=f"✔  «{nom}» илова шуд").open()
        else:
            self._add_field.helper_text      = "⚠  Ин ном аллакай мавҷуд аст"
            self._add_field.helper_text_mode = "on_error"
            self._add_field.error            = True

    def _delete(self, key):
        dlg = MDDialog(
            text=f"Ноҳияи «{key}» ва ҳамаи калимаҳояш ҳазф шаванд?",
            buttons=[
                MDFlatButton(text="Бекор"),
                MDRaisedButton(
                    text="✕  Ҳазф",
                    md_bg_color=(0.65, 0.1, 0.1, 1),
                    on_release=lambda x: self._confirm_delete(key, dlg),
                ),
            ],
        )
        dlg.open()

    def _confirm_delete(self, key, dlg):
        db.delete_dialect(key)
        dlg.dismiss()
        self.refresh()
        Snackbar(text=f"✔  «{key}» ҳазф шуд").open()


class SettingsTab(MDScreen):
    _API_FILE    = os.path.join(_DB_DIR, ".api_key")
    _UPDATE_FILE = os.path.join(_DB_DIR, ".update_config")

    def on_enter(self):
        import json
        if os.path.exists(self._API_FILE):
            with open(self._API_FILE) as f:
                self.ids.api_key_field.text = f.read().strip()
        if os.path.exists(self._UPDATE_FILE):
            try:
                with open(self._UPDATE_FILE) as f:
                    self.ids.update_url_field.text = json.load(f).get("base_url", "")
            except Exception:
                pass

    def save_settings(self):
        import json
        key = self.ids.api_key_field.text.strip()
        url = self.ids.update_url_field.text.strip()
        if key:
            with open(self._API_FILE, "w") as f:
                f.write(key)
        if url:
            if not url.endswith("/"):
                url += "/"
            with open(self._UPDATE_FILE, "w") as f:
                json.dump({"base_url": url}, f)
        Snackbar(text="✔  Танзимот захира шуд").open()


class MainScreen(MDScreen):
    def tab_analysis(self):
        self.ids.tab_mgr.current = "analysis"

    def tab_dialects(self):
        self.ids.tab_mgr.current = "dialects"
        self.ids.tab_mgr.get_screen("dialects").refresh()

    def tab_settings(self):
        self.ids.tab_mgr.current = "settings"
        self.ids.tab_mgr.get_screen("settings").on_enter()


# ─────────────────────────────────────────────────────────────────────────────
# Барнома
# ─────────────────────────────────────────────────────────────────────────────

class TajikDialectApp(MDApp):
    current_user = None

    def build(self):
        self.title = "Лаҳҷаҳои Тоҷикистон"
        self.theme_cls.theme_style  = "Dark"
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.accent_palette  = "Red"

        if _IS_ANDROID:
            try:
                from android import activity  # type: ignore
                activity.bind(on_activity_result=self._on_activity_result)
            except Exception:
                pass

        sm = MDScreenManager()
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(MainScreen(name="main"))
        sm.current = "login"
        return sm

    def _on_activity_result(self, request_code, result_code, data):
        if request_code != _VOICE_REQUEST:
            return
        RESULT_OK = -1
        try:
            main = self.root.get_screen("main")
            tab  = main.ids.tab_mgr.get_screen("analysis")
            tab._set_mic_state(False)
            if result_code == RESULT_OK and data:
                from jnius import autoclass  # type: ignore
                results = data.getStringArrayListExtra("android.speech.extra.RESULTS")
                if results and results.size() > 0:
                    Clock.schedule_once(
                        lambda dt: tab._insert_voice_text(results.get(0)), 0)
        except Exception as e:
            pass


if __name__ == "__main__":
    TajikDialectApp().run()
