[app]
title = Lahchahoi Tojikiston
package.name = tajikdialect
package.domain = org.tajikdialect
version = 1.2.0

source.dir = .
source.include_exts = py,png,jpg,jpeg,json,db
source.exclude_dirs = .github,__pycache__,.git,templates,static,dist,build

entrypoint = kivy_app.py

requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow,plyer

orientation = portrait
fullscreen = 0

android.minapi = 21
android.api = 33
android.ndk = 25b
android.archs = arm64-v8a
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,RECORD_AUDIO
android.allow_backup = True
android.icon = icon.png

[buildozer]
log_level = 2
warn_on_root = 1
