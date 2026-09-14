@echo off
title B2B Ton Advisor Telegram Bot
cd /d "%~dp0"
echo ======================================================
echo    B2B TON ADVISOR - TELEGRAM BOT LISTENER
echo    Trang thai: Dang lang nghe lenh tren Telegram...
echo ======================================================
python -u b2b_ton_advisor.py --listen
pause
