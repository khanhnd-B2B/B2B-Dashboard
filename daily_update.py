import pandas as pd
import datetime
import os
import sys
import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SPREADSHEET_ID = '1YNuLmUv6FRVMieyQy4JVnFscvkqnBdygzaWaQvOWMzU'
RANGE_NAME = 'DataSorting'
MASTER_FILE = 'Data B2B Master.xlsx'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

print(f'[{datetime.datetime.now()}] Bat dau keo du lieu tu Google Sheets API (Tab {RANGE_NAME})...')

def get_google_service():
    sources = []
    
    # 1. advisor_config.json (google_token_b64) - Nguồn ưu tiên vì luôn được đồng bộ trong Git
    if os.path.exists('advisor_config.json'):
        try:
            import base64
            with open('advisor_config.json', 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            b64_token = cfg.get('google_token_b64')
            if b64_token:
                tdata = json.loads(base64.b64decode(b64_token).decode('utf-8'))
                sources.append(('advisor_config.json (google_token_b64)', tdata))
        except Exception as e:
            print(f"Lỗi đọc advisor_config.json: {e}")

    # 2. token.json
    if os.path.exists('token.json'):
        try:
            with open('token.json', 'r', encoding='utf-8') as f:
                sources.append(('token.json', json.load(f)))
        except Exception as e:
            print(f"Lỗi đọc token.json: {e}")

    # 3. Biến môi trường GOOGLE_TOKEN
    env_token = os.environ.get('GOOGLE_TOKEN')
    if env_token:
        try:
            import base64
            try:
                tdata = json.loads(env_token)
            except Exception:
                tdata = json.loads(base64.b64decode(env_token).decode('utf-8'))
            sources.append(('GOOGLE_TOKEN env', tdata))
        except Exception as e:
            print(f"Lỗi đọc GOOGLE_TOKEN env: {e}")

    if not sources:
        print('ERROR: Không tìm thấy bất kỳ nguồn xác thực Google nào (advisor_config.json, token.json hoặc GOOGLE_TOKEN).')
        return None

    for name, tdata in sources:
        try:
            creds = Credentials.from_authorized_user_info(tdata, SCOPES)
            if creds.expired and creds.refresh_token:
                print(f"Token từ {name} đã hết hạn, đang tự động làm mới...")
                creds.refresh(Request())
                print(f"✅ Làm mới token từ {name} thành công!")
                
                # Lưu lại token mới vào advisor_config.json để duy trì token tươi
                try:
                    import base64
                    with open('advisor_config.json', 'r', encoding='utf-8') as f:
                        cfg = json.load(f)
                    cfg['google_token_b64'] = base64.b64encode(creds.to_json().encode('utf-8')).decode('utf-8')
                    with open('advisor_config.json', 'w', encoding='utf-8') as f:
                        json.dump(cfg, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                try:
                    with open('token.json', 'w', encoding='utf-8') as f:
                        f.write(creds.to_json())
                except Exception:
                    pass

            service = build('sheets', 'v4', credentials=creds)
            # Thử gọi kiểm tra quyền truy cập Sheet
            service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID, fields='spreadsheetId').execute()
            print(f"✅ Kết nối Google Sheets API thành công từ nguồn: {name}!")
            return service
        except Exception as e:
            print(f"⚠️ Nguồn xác thực {name} không thành công ({e}). Đang thử nguồn dự phòng tiếp theo...")

    return None

try:
    service = get_google_service()
    if not service:
        print('❌ Không thể kết nối Google Sheets bằng bất kỳ nguồn xác thực nào!')
        sys.exit(1)

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

    # 2. Cập nhật dữ liệu lịch tải 7 ngày từ tab LichTaiUpdate7Ngay
    TRUCK_RANGE = 'LichTaiUpdate7Ngay'
    TRUCK_FILE = 'LichTaiUpdate7Ngay.xlsx'
    print(f'[{datetime.datetime.now()}] Đang kéo dữ liệu lịch tải 7 ngày (Tab {TRUCK_RANGE})...')
    try:
        result_truck = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=TRUCK_RANGE).execute()
        values_truck = result_truck.get('values', [])
        if values_truck and len(values_truck) >= 2:
            df_truck = pd.DataFrame(values_truck[1:], columns=values_truck[0])
            df_truck.to_excel(TRUCK_FILE, index=False)
            print(f'✅ Cập nhật thành công {len(df_truck)} chuyến lịch tải 7 ngày vào {TRUCK_FILE}!')
        else:
            print(f'⚠️ Tab {TRUCK_RANGE} rỗng hoặc không có dữ liệu.')
    except Exception as e_truck:
        print(f'⚠️ Lỗi khi kéo tab {TRUCK_RANGE}: {e_truck}')

except Exception as e:
    print(f'❌ Lỗi cập nhật dữ liệu: {str(e)}')
    sys.exit(1)
