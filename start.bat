@echo off
REM TR YouTube 24H Live Studio — Windows local server start
cd /d %~dp0
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
pip install -q -r requirements.txt
if not exist .env copy .env.example .env
echo Edit .env and set TR_LIVE_ADMIN_TOKEN, then run this file again.
python backend.py
pause
