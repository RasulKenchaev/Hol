[app]
title           = Лахчахои Точикистон
package.name    = tajikdialect
package.domain  = org.tajikdialect

source.dir      = .
source.include_exts = py,png,jpg,json,db
source.exclude_dirs = .github, __pycache__, .git, static, templates

version         = 1.2.0
entrypoint      = kivy_app.py

requirements    = python3,kivy==2.3.0,kivymd==1.2.0,pillow,sqlite3

orientation     = portrait
fullscreen      = 0

android.minapi          = 21
android.api             = 34
android.ndk             = 25b
android.archs           = arm64-v8a
android.permissions     = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.allow_backup    = True

[buildozer]
log_level = 1
warn_on_root = 1
