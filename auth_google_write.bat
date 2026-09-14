@echo off
title Cap quyen ghi Google Sheet cho Bot
cd /d "%~dp0"
echo ======================================================
echo    CAP QUYEN GHI GOOGLE SHEET CHO BOT
echo    Trinh duyet se tu dong mo trang dang nhap Google.
echo    Vui long chon tai khoan va bam "Cho phep" (Allow).
echo ======================================================
python auth_google.py
pause
