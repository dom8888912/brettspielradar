\
@echo off
setlocal
if not exist .venv ( py -m venv .venv )
call .venv\Scripts\activate.bat
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py scripts\fetch_offers_stub.py
py scripts\build.py
echo Server: http://localhost:8000  (STRG+C stop)
py -m http.server -d dist 8000
