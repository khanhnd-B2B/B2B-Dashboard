import pandas as pd
import datetime
import os
import sys
import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SPREADSHEET_ID = '1YNuLmUv6FRVMieyQy4JVnFscvkqnBdygzaWaQvOWMzU'
RANGE_NAME = 'DataSorting'
MASTER_FILE = 'Data B2B Master.xlsx'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

print(f'[{datetime.datetime.now()}] Bắt đầu kéo dữ liệu từ Google Sheets API (Tab {RANGE_NAME})...')

try:
    creds = None
    env_token = os.environ.get('GOOGLE_TOKEN')
    if env_token:
        try:
            creds = Credentials.from_authorized_user_info(json.loads(env_token), SCOPES)
            print("Đã nạp credentials từ biến môi trường GOOGLE_TOKEN.")
        except Exception as e:
            print(f"Lỗi đọc GOOGLE_TOKEN từ môi trường: {e}")

    if not creds and os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        print("Đã nạp credentials từ file token.json.")

    if not creds:
        print('ERROR: Không tìm thấy xác thực Google (token.json hoặc biến GOOGLE_TOKEN).')
        sys.exit(1)

    if creds.expired and creds.refresh_token:
        print("Token đã hết hạn, đang tự động làm mới qua refresh_token...")
        creds.refresh(Request())
        if os.path.exists('token.json'):
            try:
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
                print("Đã cập nhật token mới vào token.json.")
            except Exception:
                pass

    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()

    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])

    if not values or len(values) < 2:
        print('Cảnh báo: Không có dữ liệu trong Sheet hoặc bảng rỗng.')
        sys.exit(0)

    df_new = pd.DataFrame(values[1:], columns=values[0])
    print(f'Đã lấy thành công {len(df_new)} dòng dữ liệu mới từ Google Sheet.')

    if not os.path.exists(MASTER_FILE):
        df_combined = df_new
    else:
        df_master = pd.read_excel(MASTER_FILE)
        print(f'File {MASTER_FILE} hiện có: {len(df_master)} dòng.')
        df_combined = pd.concat([df_master, df_new], ignore_index=True)

    if 'MaDonGoc' in df_combined.columns:
        before_len = len(df_combined)
        df_combined = df_combined.drop_duplicates(subset=['MaDonGoc'], keep='last')
        after_len = len(df_combined)
        print(f'Đã loại bỏ {before_len - after_len} dòng trùng lặp. Tổng đơn mới: {after_len} dòng.')

    df_combined.to_excel(MASTER_FILE, index=False)
    print(f'✅ Cập nhật thành công vào {MASTER_FILE}!')

except Exception as e:
    print(f'❌ Lỗi cập nhật dữ liệu: {str(e)}')
    sys.exit(1)
