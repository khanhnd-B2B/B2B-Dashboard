cd /d D:\LophocAI\quanlyB2B
python daily_update.py
git add "Data B2B Master.xlsx" "LichTaiUpdate7Ngay.xlsx" advisor_config.json
git commit -m "data: auto update via Windows Task Scheduler"
git push origin main

