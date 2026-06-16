[app]
title           = Lahchahoi Tojikiston
package.name    = tajikdialect
package.domain  = org.tajikdialect

source.dir      = .
source.include_exts = py,png,jpg,jpeg,json,db,kv
source.exclude_dirs = .github,__pycache__,.git,templates,static,dist,build

version         = 1.2.0
entrypoint      = kivy_app.py

requirements    = python3,kivy==2.3.0,kivymd==1.2.0,pillow,plyer

orientation     = portrait
fullscreen      = 0

android.minapi          = 21
android.api             = 34
android.ndk             = 25b
android.archs           = arm64-v8a
android.permissions     = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,RECORD_AUDIO
android.allow_backup    = True
android.icon            = icon.png
android.presplash       = icon.png
android.presplash_color = #0D1B2A

# ── Имзои релиз (пеш аз нашр пур кунед) ─────────────────────────────────────
# Барои сохтани калид:
#   keytool -genkey -v -keystore tajik.keystore -keyalg RSA -keysize 2048 -validity 10000 -alias tajikdialect
#
# android.release_artifact = aab
# android.keystore         = tajik.keystore
# android.keystore_alias   = tajikdialect
# android.keystore_passwd  = ПАРОЛ_ШУМО
# android.key_passwd       = ПАРОЛ_КАЛИД

[buildozer]
log_level = 1
warn_on_root = 1
