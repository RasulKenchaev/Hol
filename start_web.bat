@echo off
chcp 65001 >nul
echo.
echo  ================================================
echo   Лахчахои Точикистон — Веб-барнома
echo  ================================================
echo.

cd /d "%~dp0"

python -c "import socket; s=socket.socket(); s.connect(('8.8.8.8',80)); print('  Аз телефон кушоед:  http://'+s.getsockname()[0]+':5050'); s.close()" 2>nul
echo  Аз компютер кушоед:  http://localhost:5050
echo.

python -c "import webbrowser,threading,time; threading.Timer(1.5, lambda: webbrowser.open('http://localhost:5050')).start()"

python web_app.py

pause
