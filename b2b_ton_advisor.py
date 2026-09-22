import requests
import json
import pandas as pd
import re
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# Cố định múi giờ Việt Nam (GMT+7) cho Cloud Server (Render chạy UTC)
VN_TZ = timezone(timedelta(hours=7))

def get_vietnam_now():
    """Lấy thời gian hiện tại chuẩn Việt Nam (GMT+7) dù chạy trên máy tính hay Cloud Server."""
    return datetime.now(timezone.utc).astimezone(VN_TZ).replace(tzinfo=None)

sys.stdout.reconfigure(encoding='utf-8')

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'advisor_config.json')

DEFAULT_CONFIG = {
    'metabase_url': 'https://data-bi.ghn.vn',
    'metabase_session': '911df869-0b66-4af3-a701-a10a563c33ad',
    'metabase_username': '',
    'metabase_password': '',
    'metabase_card_id': 6287,
    'telegram_bot_token': '8370307476:AAEsPB2UZ0zQHMTEWPGFFBw7fUYuWsePxPM',
    'telegram_chat_id': '-1004492922071',
    'telegram_message_thread_id': 7090,
    'gg_sheet_url': 'https://docs.google.com/spreadsheets/d/1YNuLmUv6FRVMieyQy4JVnFscvkqnBdygzaWaQvOWMzU/edit?gid=654306746#gid=654306746'
}

TRUCK_FILE = os.path.join(os.path.dirname(__file__), 'data chuyến Truck 7 ngày 11.09.xlsx')

PREFIX_TO_PROVINCE = {
    # Miền Bắc
    'HNO': 'Hà Nội', 'HN': 'Hà Nội', 'HAN': 'Hà Nội',
    'BNI': 'Bắc Ninh', 'BN': 'Bắc Ninh',
    'BGI': 'Bắc Giang', 'BG': 'Bắc Giang',
    'QNI': 'Quảng Ninh', 'QN': 'Quảng Ninh',
    'HPG': 'Hải Phòng', 'HP': 'Hải Phòng', 'HPH': 'Hải Phòng',
    'HDU': 'Hải Dương', 'HD': 'Hải Dương',
    'HYE': 'Hưng Yên', 'HY': 'Hưng Yên',
    'NDI': 'Nam Định', 'NĐ': 'Nam Định', 'NAM': 'Nam Định',
    'NBI': 'Ninh Bình', 'NB': 'Ninh Bình',
    'TBH': 'Thái Bình', 'TB': 'Thái Bình', 'TBI': 'Thái Bình',
    'HNA': 'Hà Nam', 'HNAM': 'Hà Nam',
    'THN': 'Thái Nguyên', 'TN': 'Thái Nguyên', 'TNG': 'Thái Nguyên',
    'LSN': 'Lạng Sơn', 'LS': 'Lạng Sơn', 'LSO': 'Lạng Sơn',
    'PTO': 'Phú Thọ', 'PT': 'Phú Thọ', 'PTH': 'Phú Thọ',
    'VPH': 'Vĩnh Phúc', 'VP': 'Vĩnh Phúc',
    'HBI': 'Hòa Bình', 'HB': 'Hòa Bình',
    'SLA': 'Sơn La', 'SL': 'Sơn La',
    'LCA': 'Lào Cai', 'LC': 'Lào Cai',
    'YBA': 'Yên Bái', 'YB': 'Yên Bái',
    'TQG': 'Tuyên Quang', 'TQ': 'Tuyên Quang', 'TQU': 'Tuyên Quang',
    'HAG': 'Hà Giang', 'HG': 'Hà Giang',
    'BKA': 'Bắc Kạn', 'BK': 'Bắc Kạn',
    'CBG': 'Cao Bằng', 'CBA': 'Cao Bằng', 'CB': 'Cao Bằng',
    'DBI': 'Điện Biên', 'ĐB': 'Điện Biên', 'DB': 'Điện Biên',
    'LCH': 'Lai Châu', 'LCU': 'Lai Châu',

    # Miền Trung & Tây Nguyên
    'THO': 'Thanh Hóa', 'TH': 'Thanh Hóa', 'THA': 'Thanh Hóa',
    'NAN': 'Nghệ An', 'NA': 'Nghệ An', 'NGA': 'Nghệ An',
    'HTI': 'Hà Tĩnh', 'HT': 'Hà Tĩnh',
    'QBI': 'Quảng Bình', 'QB': 'Quảng Bình',
    'QTI': 'Quảng Trị', 'QT': 'Quảng Trị', 'QTR': 'Quảng Trị',
    'TTH': 'Thừa Thiên Huế', 'HUE': 'Thừa Thiên Huế',
    'DNA': 'Đà Nẵng', 'ĐN': 'Đà Nẵng', 'DNG': 'Đà Nẵng',
    'QNA': 'Quảng Nam', 'QNM': 'Quảng Nam',
    'QNG': 'Quảng Ngãi', 'QNGA': 'Quảng Ngãi',
    'BDI': 'Bình Định', 'BĐ': 'Bình Định', 'BDH': 'Bình Định',
    'PYE': 'Phú Yên', 'PY': 'Phú Yên',
    'KHA': 'Khánh Hòa', 'KH': 'Khánh Hòa', 'KHO': 'Khánh Hòa',
    'NTH': 'Ninh Thuận', 'NT': 'Ninh Thuận', 'NTU': 'Ninh Thuận',
    'BTH': 'Bình Thuận', 'BT': 'Bình Thuận',
    'KTU': 'Kon Tum', 'KT': 'Kon Tum',
    'GLI': 'Gia Lai', 'GL': 'Gia Lai', 'GLA': 'Gia Lai',
    'DKL': 'Đắk Lắk', 'DLK': 'Đắk Lắk', 'DLA': 'Đắk Lắk', 'DL': 'Đắk Lắk',
    'DKN': 'Đắk Nông', 'DNO': 'Đắk Nông',
    'LDG': 'Lâm Đồng', 'LĐ': 'Lâm Đồng', 'LDO': 'Lâm Đồng',

    # Miền Nam & ĐBSCL
    'SGN': 'Hồ Chí Minh', 'HCM': 'Hồ Chí Minh',
    'BDU': 'Bình Dương', 'BD': 'Bình Dương',
    'DNI': 'Đồng Nai', 'ĐNAI': 'Đồng Nai', 'DN': 'Đồng Nai',
    'BPC': 'Bình Phước', 'BP': 'Bình Phước', 'BPH': 'Bình Phước',
    'TNI': 'Tây Ninh', 'TN': 'Tây Ninh',
    'BVT': 'Bà Rịa - Vũng Tàu', 'VT': 'Bà Rịa - Vũng Tàu', 'BRVT': 'Bà Rịa - Vũng Tàu',
    'LAN': 'Long An', 'LA': 'Long An',
    'TGI': 'Tiền Giang', 'TG': 'Tiền Giang',
    'BTR': 'Bến Tre', 'BT': 'Bến Tre',
    'DTH': 'Đồng Tháp', 'ĐT': 'Đồng Tháp',
    'AGI': 'An Giang', 'AG': 'An Giang', 'AGG': 'An Giang',
    'KGG': 'Kiên Giang', 'KG': 'Kiên Giang', 'KGI': 'Kiên Giang',
    'CTO': 'Cần Thơ', 'CT': 'Cần Thơ', 'CTH': 'Cần Thơ',
    'HGI': 'Hậu Giang', 'HG': 'Hậu Giang',
    'VLO': 'Vĩnh Long', 'VL': 'Vĩnh Long',
    'TVI': 'Trà Vinh', 'TV': 'Trà Vinh',
    'SOC': 'Sóc Trăng', 'ST': 'Sóc Trăng', 'STR': 'Sóc Trăng', 'STG': 'Sóc Trăng',
    'BLI': 'Bạc Liêu', 'BL': 'Bạc Liêu',
    'CMU': 'Cà Mau', 'CM': 'Cà Mau', 'CMA': 'Cà Mau',

    # Hubs liên vùng
    'TNB': 'Cần Thơ',
    'DNB': 'Hồ Chí Minh',
}

PROVINCES_LIST = [
    'Quảng Ninh', 'Bắc Giang', 'Bắc Ninh', 'Thanh Hóa', 'Thanh Hoá', 'Nghệ An',
    'Hải Phòng', 'Hải Dương', 'Hưng Yên', 'Nam Định', 'Ninh Bình', 'Thái Bình',
    'Hà Nam', 'Thái Nguyên', 'Lạng Sơn', 'Phú Thọ', 'Vĩnh Phúc', 'Hòa Bình',
    'Hoà Bình', 'Sơn La', 'Lào Cai', 'Yên Bái', 'Tuyên Quang', 'Hà Giang',
    'Đà Nẵng', 'Hồ Chí Minh', 'HCM', 'Bình Dương', 'Đồng Nai', 'Long An',
    'Bình Phước', 'Bình Thuận', 'Quảng Bình', 'Quảng Trị', 'Thừa Thiên Huế',
    'Huế', 'Quảng Nam', 'Quảng Ngãi', 'Bình Định', 'Phú Yên', 'Khánh Hòa',
    'Khánh Hoà', 'Gia Lai', 'Đắk Lắk', 'Đắk Nông', 'Lâm Đồng', 'Cần Thơ',
    'Kiên Giang', 'An Giang', 'Cà Mau', 'Hà Nội', 'Hà Tĩnh', 'Bà Rịa - Vũng Tàu',
    'BRVT', 'Đồng Tháp', 'Trà Vinh', 'Ninh Thuận', 'Tây Ninh', 'Bến Tre',
    'Vĩnh Long', 'Sóc Trăng', 'Bạc Liêu', 'Hậu Giang', 'Tiền Giang', 'Điện Biên',
    'Lai Châu', 'Bắc Kạn', 'Cao Bằng', 'Kon Tum'
]

HN_KEYWORDS = [
    'hà nội', 'ha noi', 'long biên', 'thanh xuân', 'hoài đức', 'cầu giấy', 'ba đình',
    'đông anh', 'mê linh', 'sóc sơn', 'tây hồ', 'hoàn kiếm', 'đống đa', 'hai bà trưng',
    'thanh trì', 'hoàng mai', 'hà đông', 'nam từ liêm', 'bắc từ liêm', 'phúc thọ', 'ứng hòa',
    'ứng hoà', 'thường tín', 'phú xuyên', 'mỹ đức', 'chương mỹ', 'thanh oai', 'đan phượng',
    'thạch thất', 'quốc oai', 'ba vì', 'sơn tây', 'gia lâm'
]

CITY_DISTRICT_TO_PROVINCE = {
    # Khánh Hòa
    'nha trang': 'Khánh Hòa', 'cam ranh': 'Khánh Hòa', 'cam lâm': 'Khánh Hòa',
    'ninh hòa': 'Khánh Hòa', 'diên khánh': 'Khánh Hòa', 'vạn ninh': 'Khánh Hòa',
    'khánh vĩnh': 'Khánh Hòa', 'khánh sơn': 'Khánh Hòa',
    # Lâm Đồng
    'đà lạt': 'Lâm Đồng', 'da lat': 'Lâm Đồng', 'bảo lộc': 'Lâm Đồng', 'đức trọng': 'Lâm Đồng',
    'di linh': 'Lâm Đồng', 'đơn dương': 'Lâm Đồng', 'lâm hà': 'Lâm Đồng',
    # Đắk Lắk
    'buôn ma thuột': 'Đắk Lắk', 'bmt': 'Đắk Lắk', 'buôn hồ': 'Đắk Lắk', 'ea h\'leo': 'Đắk Lắk',
    'krông năng': 'Đắk Lắk', 'krông pắc': 'Đắk Lắk', 'cư m\'gar': 'Đắk Lắk',
    # Gia Lai
    'pleiku': 'Gia Lai', 'an khê': 'Gia Lai', 'ayun pa': 'Gia Lai', 'chư sê': 'Gia Lai',
    # Bình Thuận / Ninh Thuận
    'phan thiết': 'Bình Thuận', 'la gi': 'Bình Thuận', 'phan rang': 'Ninh Thuận',
    # Bình Định
    'quy nhơn': 'Bình Định', 'an nhơn': 'Bình Định', 'hoài nhơn': 'Bình Định',
    # BRVT
    'vũng tàu': 'Bà Rịa - Vũng Tàu', 'bà rịa': 'Bà Rịa - Vũng Tàu', 'phú mỹ': 'Bà Rịa - Vũng Tàu',
    'hồ tràm': 'Bà Rịa - Vũng Tàu', 'xuyên mộc': 'Bà Rịa - Vũng Tàu', 'long điền': 'Bà Rịa - Vũng Tàu',
    # Tây Nam Bộ
    'tnb': 'Cần Thơ', 'tây nam bộ': 'Cần Thơ', 'ninh kiều': 'Cần Thơ', 'cái răng': 'Cần Thơ',
    'long xuyên': 'An Giang', 'châu đốc': 'An Giang', 'rạch giá': 'Kiên Giang', 'hà tiên': 'Kiên Giang',
    'mỹ tho': 'Tiền Giang', 'tân an': 'Long An', 'bến tre': 'Bến Tre', 'trà vinh': 'Trà Vinh',
    'vĩnh long': 'Vĩnh Long', 'sóc trăng': 'Sóc Trăng', 'bạc liêu': 'Bạc Liêu', 'cà mau': 'Cà Mau',
    # Miền Trung
    'tam kỳ': 'Quảng Nam', 'hội an': 'Quảng Nam',
    'huế': 'Thừa Thiên Huế', 'đồng hới': 'Quảng Bình', 'đông hà': 'Quảng Trị',
    'vinh': 'Nghệ An', 'cửa lò': 'Nghệ An', 'sầm sơn': 'Thanh Hóa', 'bỉm sơn': 'Thanh Hóa',
    # Miền Bắc
    'hạ long': 'Quảng Ninh', 'cẩm phả': 'Quảng Ninh', 'móng cái': 'Quảng Ninh', 'uông bí': 'Quảng Ninh',
    'thủy nguyên': 'Hải Phòng', 'chí linh': 'Hải Dương', 'từ sơn': 'Bắc Ninh',
    'việt yên': 'Bắc Giang', 'sông công': 'Thái Nguyên'
}

NO_ROUTE_ADVICE_PROVINCES = {'Hà Nội', 'Bắc Ninh'}

def is_no_route_province(p):
    p_lower = str(p).strip().lower()
    return p_lower in ['hà nội', 'ha noi', 'bắc ninh', 'bac ninh']

def extract_province(name):
    name = str(name).strip()
    if not name or name == 'nan':
        return 'Khác'

    # 1. Check mã tỉnh trong ngoặc đơn, ví dụ (KHO), (HN), (GLA), (BVT)...
    m = re.match(r'^\(([A-Za-z0-9]+)\)', name)
    if m:
        pfx = m.group(1).upper()
        if pfx in PREFIX_TO_PROVINCE:
            return PREFIX_TO_PROVINCE[pfx]

    # 2. Check phần đuôi sau dấu gạch ngang cuối cùng, ví dụ ...-HN, ...-HCM, ...-Đà Nẵng
    parts = [p.strip() for p in name.split('-')]
    if len(parts) >= 2:
        last_part = parts[-1]
        last_upper = last_part.upper()
        if last_upper in PREFIX_TO_PROVINCE:
            return PREFIX_TO_PROVINCE[last_upper]
        for p in PROVINCES_LIST:
            if p.lower() == last_part.lower():
                if 'thanh ho' in p.lower(): return 'Thanh Hóa'
                if 'hoà bình' in p.lower() or 'hòa bình' in p.lower(): return 'Hòa Bình'
                if 'khánh ho' in p.lower(): return 'Khánh Hòa'
                if 'brvt' in p.lower() or 'vũng tàu' in p.lower(): return 'Bà Rịa - Vũng Tàu'
                if p == 'HCM': return 'Hồ Chí Minh'
                return p

    # 3. Check tên tỉnh trực tiếp trong chuỗi
    for p in PROVINCES_LIST:
        pattern = r'(?i)(?:\b|_|-|\s|^)' + re.escape(p) + r'(?:\b|_|-|\s|$)'
        if re.search(pattern, name):
            if 'thanh ho' in p.lower(): return 'Thanh Hóa'
            if 'hoà bình' in p.lower() or 'hòa bình' in p.lower(): return 'Hòa Bình'
            if 'khánh ho' in p.lower(): return 'Khánh Hòa'
            if 'brvt' in p.lower() or 'vũng tàu' in p.lower(): return 'Bà Rịa - Vũng Tàu'
            if 'thừa thiên huế' in p.lower() or p == 'Huế': return 'Thừa Thiên Huế'
            if p == 'HCM': return 'Hồ Chí Minh'
            return p

    # 4. Check từ khóa thành phố/huyện trực thuộc tỉnh
    name_lower = name.lower()
    for kw, prov in CITY_DISTRICT_TO_PROVINCE.items():
        pattern = r'(?i)(?:\b|_|-|\s|^)' + re.escape(kw) + r'(?:\b|_|-|\s|$)'
        if re.search(pattern, name_lower):
            return prov

    # 5. Check các quận/huyện Hà Nội
    for kw in HN_KEYWORDS:
        pattern = r'(?i)(?:\b|_|-|\s|^)' + re.escape(kw) + r'(?:\b|_|-|\s|$)'
        if re.search(pattern, name_lower):
            return 'Hà Nội'

    return 'Khác'

VALID_ORIGINS = [
    'Kho B2B - Đài Tư - Hà Nội',
    'Kho Trung Chuyển Hà Nội 02'
]

ORIGIN_EXCLUDED_STOPS = {
    'kho b2b - đài tư - hà nội',
    'kho trung chuyển hà nội 02'
}

def start_health_server(port=8080):
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b"<h1>B2B Ton Advisor Bot is Running Online 24/7!</h1><p>Status: OK</p>")

        def do_HEAD(self):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()

        def do_POST(self):
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(b"OK")

        def log_message(self, format, *args):
            pass

    try:
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        print(f"🌐 Đã khởi chạy Health Server trên port {port} (hỗ trợ Render/Railway 24/7)")
    except Exception as e:
        print(f"Không thể mở Health Server trên port {port}: {e}")

class B2BTonAdvisor:
    def __init__(self):
        self.load_config()
        self._load_truck_data()

    def load_config(self):
        cfg = DEFAULT_CONFIG.copy()
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    file_cfg = json.load(f)
                    cfg.update(file_cfg)
            except Exception as e:
                print(f"Lỗi đọc file cấu hình {CONFIG_FILE}: {e}")

        self.config = cfg

        # Allow environment overrides
        self.metabase_url = os.environ.get('METABASE_URL', cfg.get('metabase_url', 'https://data-bi.ghn.vn'))
        self.session_token = os.environ.get('METABASE_SESSION', cfg.get('metabase_session', ''))
        self.metabase_username = os.environ.get('METABASE_USERNAME', cfg.get('metabase_username', ''))
        self.metabase_password = os.environ.get('METABASE_PASSWORD', cfg.get('metabase_password', ''))
        self.card_id = int(os.environ.get('METABASE_CARD_ID', cfg.get('metabase_card_id', 6287)))
        self.bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', cfg.get('telegram_bot_token', ''))
        self.chat_id = os.environ.get('TELEGRAM_CHAT_ID', cfg.get('telegram_chat_id', ''))
        self.thread_id = int(os.environ.get('TELEGRAM_MESSAGE_THREAD_ID', cfg.get('telegram_message_thread_id', 7090)))
        self.gg_sheet_url = os.environ.get('GG_SHEET_URL', cfg.get('gg_sheet_url', ''))
        m = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', self.gg_sheet_url)
        self.spreadsheet_id = m.group(1) if m else '1YNuLmUv6FRVMieyQy4JVnFscvkqnBdygzaWaQvOWMzU'
        self.last_excluded_count = 0

    def save_config(self):
        m = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', self.gg_sheet_url)
        if m:
            self.spreadsheet_id = m.group(1)
        cfg = getattr(self, 'config', {}).copy()
        cfg.update({
            'metabase_url': self.metabase_url,
            'metabase_session': self.session_token,
            'metabase_username': self.metabase_username,
            'metabase_password': self.metabase_password,
            'metabase_card_id': self.card_id,
            'telegram_bot_token': self.bot_token,
            'telegram_chat_id': self.chat_id,
            'telegram_message_thread_id': self.thread_id,
            'gg_sheet_url': self.gg_sheet_url
        })
        self.config = cfg
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            print(f"✅ Đã lưu cấu hình mới vào {CONFIG_FILE}")
        except Exception as e:
            print(f"❌ Lỗi lưu cấu hình: {e}")

    def _load_truck_data(self):
        if not os.path.exists(TRUCK_FILE):
            print(f"Warning: Không tìm thấy file {TRUCK_FILE}")
            self.df_truck = None
            return

        self.df_truck = pd.read_excel(TRUCK_FILE, header=1)
        self.df_truck['GioDuKienDen_GMT7'] = pd.to_datetime(self.df_truck['GioDuKienDen_GMT7'], errors='coerce')
        self.df_truck['HHMM'] = self.df_truck['GioDuKienDen_GMT7'].dt.strftime('%H:%M')

        # Filter trips starting at Đài Tư or HN02, strictly excluding HY_ routes
        stop1 = self.df_truck[self.df_truck['ThuTuDiem'] == 1]
        valid_stop1 = stop1[stop1['TenDiem'].isin(VALID_ORIGINS)].copy()
        self.b2b_stop1 = valid_stop1[~valid_stop1['MaTuyen'].str.upper().str.startswith('HY_')].copy()

    def login_metabase(self, username=None, password=None):
        """Tự động đăng nhập Metabase bằng tài khoản username/password để lấy session token mới."""
        uname = (username or self.metabase_username or '').strip()
        pword = (password or self.metabase_password or '').strip()
        if not uname or not pword:
            print("⚠️ Chưa có thông tin tài khoản Metabase (username/password) để tự động đăng nhập.")
            return False, "Chưa cấu hình tài khoản hoặc mật khẩu Metabase"

        login_url = f'{self.metabase_url}/api/session'
        try:
            print(f"🔄 Đang tự động gửi yêu cầu đăng nhập tới Metabase ({uname})...")
            res = requests.post(login_url, json={'username': uname, 'password': pword}, timeout=25)
            if res.status_code == 200:
                data = res.json()
                new_session = data.get('id')
                if new_session:
                    self.session_token = new_session
                    self.metabase_username = uname
                    self.metabase_password = pword
                    self.save_config()
                    print(f"✅ Đăng nhập Metabase thành công! Session ID mới: {new_session[:8]}***")
                    return True, new_session

            err_msg = "Sai tài khoản hoặc mật khẩu"
            try:
                err_data = res.json()
                if 'errors' in err_data:
                    err_msg = ", ".join([f"{k}: {v}" for k, v in err_data['errors'].items()])
                elif 'message' in err_data:
                    err_msg = err_data['message']
            except Exception:
                err_msg = res.text[:200]
            print(f"❌ Đăng nhập Metabase thất bại ({res.status_code}): {err_msg}")
            return False, f"HTTP {res.status_code}: {err_msg}"
        except Exception as e:
            print(f"❌ Lỗi kết nối đăng nhập Metabase: {e}")
            return False, f"Lỗi kết nối: {str(e)}"

    def fetch_live_metabase(self):
        url = f'{self.metabase_url}/api/card/{self.card_id}/query/json'
        
        # Nếu chưa có session token nhưng có tài khoản mật khẩu, thử đăng nhập trước
        if not self.session_token and self.metabase_username and self.metabase_password:
            self.login_metabase()

        headers = {
            'X-Metabase-Session': self.session_token or '',
            'Cookie': f'metabase.SESSION={self.session_token or ""}',
            'Content-Type': 'application/json'
        }
        res = requests.post(url, headers=headers, json={}, timeout=40)
        
        # Nếu session hết hạn (401), tự động đăng nhập lại bằng username/password nếu có
        if res.status_code == 401 and self.metabase_username and self.metabase_password:
            print("⚠️ Session Metabase đã hết hạn (401). Đang tự động đăng nhập lại để cấp token mới...")
            ok, msg = self.login_metabase()
            if ok:
                headers['X-Metabase-Session'] = self.session_token
                headers['Cookie'] = f'metabase.SESSION={self.session_token}'
                res = requests.post(url, headers=headers, json={}, timeout=40)
            else:
                raise Exception(f"Session Metabase hết hạn và tự động đăng nhập thất bại: {msg}")

        res.raise_for_status()
        return pd.DataFrame(res.json())

    def get_google_credentials(self):
        """Lấy xác thực Google từ GOOGLE_TOKEN, advisor_config.json hoặc token.json."""
        token_path = os.path.join(os.path.dirname(__file__), 'token.json')
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        import base64

        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        creds = None

        # 1. Biến môi trường GOOGLE_TOKEN (chuỗi JSON hoặc base64)
        env_token = os.environ.get('GOOGLE_TOKEN')
        if env_token:
            try:
                try:
                    token_data = json.loads(env_token)
                except Exception:
                    token_data = json.loads(base64.b64decode(env_token).decode('utf-8'))
                creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            except Exception as e:
                print(f"Lỗi nạp GOOGLE_TOKEN từ môi trường: {e}")

        # 2. File advisor_config.json đã lưu (google_token_b64)
        if not creds:
            b64_token = getattr(self, 'config', {}).get('google_token_b64')
            if not b64_token and os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                        b64_token = json.load(f).get('google_token_b64')
                except Exception:
                    pass
            if b64_token:
                try:
                    token_data = json.loads(base64.b64decode(b64_token).decode('utf-8'))
                    creds = Credentials.from_authorized_user_info(token_data, SCOPES)
                except Exception as e:
                    print(f"Lỗi nạp google_token_b64 từ advisor_config.json: {e}")

        # 3. File token.json
        if not creds and os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            except Exception as e:
                print(f"Lỗi nạp token.json: {e}")

        if not creds:
            return None

        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                if hasattr(self, 'config') and 'google_token_b64' in self.config:
                    self.config['google_token_b64'] = base64.b64encode(creds.to_json().encode('utf-8')).decode('utf-8')
                    self.save_config()
                if os.path.exists(token_path):
                    try:
                        with open(token_path, 'w') as token:
                            token.write(creds.to_json())
                    except Exception:
                        pass
            except Exception as e:
                print(f"Lỗi refresh google token: {e}")

        return creds

    def fetch_live_sheet_backlog(self):
        """Đọc trực tiếp dữ liệu đơn tồn từ Google Sheet tab TonUpdate1h, so sánh với DataSorting để loại đơn đã xuất kho."""
        creds = self.get_google_credentials()
        if not creds:
            raise Exception("Không tìm thấy xác thực Google (advisor_config.json, token.json hoặc biến môi trường GOOGLE_TOKEN)")

        from googleapiclient.discovery import build
        service = build('sheets', 'v4', credentials=creds)
        tab_name = 'TonUpdate1h'

        ranges = [f'{tab_name}!A1:Z', 'DataSorting!E:S']
        try:
            res = service.spreadsheets().values().batchGet(spreadsheetId=self.spreadsheet_id, ranges=ranges).execute()
            value_ranges = res.get('valueRanges', [])
            values = value_ranges[0].get('values', []) if len(value_ranges) > 0 else []
            sort_values = value_ranges[1].get('values', []) if len(value_ranges) > 1 else []
        except Exception as e_batch:
            print(f"Lỗi batchGet, chuyển sang get riêng lẻ tab {tab_name}: {e_batch}")
            res = service.spreadsheets().values().get(spreadsheetId=self.spreadsheet_id, range=f'{tab_name}!A1:Z').execute()
            values = res.get('values', [])
            sort_values = []

        if not values or len(values) < 2:
            raise Exception(f"Sheet tab '{tab_name}' trống hoặc không có dữ liệu.")

        headers = values[0]
        df = pd.DataFrame(values[1:], columns=headers)

        self.last_excluded_count = 0
        # So sánh với DataSorting: nếu trạng thái cột S là "Đã xuất khỏi kho thao tác gần nhất" thì loại bỏ
        if sort_values and len(sort_values) > 1:
            try:
                sort_headers = sort_values[0]
                df_sort = pd.DataFrame(sort_values[1:], columns=sort_headers)
                col_don_sort = 'MaDonGoc' if 'MaDonGoc' in df_sort.columns else df_sort.columns[0]
                col_status_sort = 'TrangThaiViTriInside' if 'TrangThaiViTriInside' in df_sort.columns else df_sort.columns[-1]

                mask_exited = df_sort[col_status_sort].astype(str).str.strip().str.lower() == 'đã xuất khỏi kho thao tác gần nhất'.lower()
                exited_orders = set(df_sort.loc[mask_exited, col_don_sort].dropna().astype(str).str.strip())

                col_don_ton = 'MaDon' if 'MaDon' in df.columns else ('MaDonGoc' if 'MaDonGoc' in df.columns else df.columns[0])
                before_len = len(df)
                if exited_orders:
                    df = df[~df[col_don_ton].astype(str).str.strip().isin(exited_orders)].copy()
                    excluded_cnt = before_len - len(df)
                    self.last_excluded_count = excluded_cnt
                    print(f"📊 Đã loại bỏ {excluded_cnt} đơn có trạng thái 'Đã xuất khỏi kho thao tác gần nhất' (cột S DataSorting). Còn lại {len(df)} đơn tồn thực tế.")
            except Exception as e_filter:
                print(f"⚠️ Cảnh báo: Lỗi lọc đơn xuất kho từ DataSorting ({e_filter}). Tiếp tục với dữ liệu gốc {tab_name}.")

        return df

    def fetch_live_data(self):
        """Ưu tiên đọc dữ liệu tồn từ Google Sheet tab TonUpdate1h, fallback sang Metabase nếu cần."""
        try:
            print("📊 Đang đọc dữ liệu tồn từ Google Sheet tab TonUpdate1h...")
            df = self.fetch_live_sheet_backlog()
            print(f"✅ Đã nạp thành công {len(df)} dòng dữ liệu từ Google Sheet tab TonUpdate1h!")
            return df, "Google Sheet (TonUpdate1h)"
        except Exception as e_sheet:
            print(f"⚠️ Không đọc được từ Google Sheet ({e_sheet}). Đang thử kết nối Metabase...")
            try:
                df = self.fetch_live_metabase()
                return df, f"Metabase (Card {self.card_id})"
            except Exception as e_meta:
                raise Exception(f"Không thể lấy dữ liệu tồn từ cả Google Sheet ({e_sheet}) và Metabase ({e_meta})")

    def get_upcoming_trips(self, current_time, window_hours=4):
        if self.df_truck is None:
            return []

        curr_time_str = current_time.strftime('%H:%M')
        window_end = current_time + timedelta(hours=window_hours) # Khung 4h
        end_time_str = window_end.strftime('%H:%M')

        # Filter stop 1 in the window
        if end_time_str < curr_time_str:  # crosses midnight
            upcoming_stop1 = self.b2b_stop1[(self.b2b_stop1['HHMM'] >= curr_time_str) | (self.b2b_stop1['HHMM'] <= end_time_str)]
        else:
            upcoming_stop1 = self.b2b_stop1[(self.b2b_stop1['HHMM'] >= curr_time_str) & (self.b2b_stop1['HHMM'] <= end_time_str)]

        unique_trips = upcoming_stop1.drop_duplicates(subset=['MaTuyen', 'HHMM']).sort_values('HHMM')

        trips_list = []
        for _, r in unique_trips.iterrows():
            mc = r['MaChuyen']
            mt = r['MaTuyen']
            hh = r['HHMM']
            td = r['TenDiem']
            tt = r.get('TrongTai', 0)

            trip_rows = self.df_truck[self.df_truck['MaChuyen'] == mc].sort_values('ThuTuDiem')
            downstream_rows = trip_rows[trip_rows['ThuTuDiem'] > 1]
            
            # Extract provinces served from downstream destination stops
            provinces_served = set()
            for _, d_row in downstream_rows.iterrows():
                s_name = str(d_row['TenDiem']).strip()
                s_lower = s_name.lower()

                # Skip origin hubs so we don't accidentally map Hanoi local to inter-provincial trucks
                if s_lower in ORIGIN_EXCLUDED_STOPS:
                    continue

                if 'hưng yên 01' in s_lower:
                    if 'HN_HY' in mt.upper():
                        provinces_served.update(['Hưng Yên', 'Nam Định', 'Ninh Bình', 'Hải Dương', 'Thái Bình', 'Hà Nam'])
                elif 'hồ chí minh' in s_lower:
                    provinces_served.update(['Hồ Chí Minh', 'Bình Dương', 'Long An', 'Đồng Nai'])
                elif 'sóng thần' in s_lower:
                    provinces_served.update(['Bình Dương', 'Hồ Chí Minh', 'Đồng Nai', 'Bình Phước'])
                elif 'dương xá' in s_lower:
                    provinces_served.update(['Bắc Ninh', 'Hà Nội'])
                else:
                    p = extract_province(s_name)
                    if p not in ['Khác', 'Tỉnh khác']:
                        provinces_served.add(p)

            if provinces_served:
                trips_list.append({
                    'MaChuyen': mc,
                    'MaTuyen': mt,
                    'HHMM': hh,
                    'Origin': td,
                    'TrongTai': tt,
                    'ProvincesServed': provinces_served
                })

        return trips_list

    # Alias để tương thích ngược
    get_upcoming_trips_in_90min = get_upcoming_trips

    def sync_to_google_sheet(self, df_transit, upcoming_trips, now_str):
        creds = self.get_google_credentials()
        if not creds:
            print("⚠️ Không tìm thấy xác thực Google để đồng bộ Google Sheet.")
            return self.gg_sheet_url

        try:
            from googleapiclient.discovery import build
            service = build('sheets', 'v4', credentials=creds)
            spreadsheet_id = self.spreadsheet_id
            tab_name = 'Ton_Metabase_Live'

            # Build province to trip lookup
            prov_to_trips = defaultdict(list)
            for t in upcoming_trips:
                for prov in t.get('ProvincesServed', []):
                    prov_to_trips[prov].append(t)

            export_rows = []
            for _, r in df_transit.iterrows():
                prov = r.get('Tinh', '')
                matched_t = prov_to_trips.get(prov, [])
                if matched_t:
                    primary_t = matched_t[0]
                    tuyen = primary_t['MaTuyen']
                    gio = primary_t['HHMM']
                    diem = primary_t['Origin']
                    tai = primary_t.get('TrongTai', '')
                    status = 'Sắp chạy (4h)'
                else:
                    tuyen = 'Chưa có chuyến trong 4h'
                    gio = '---'
                    diem = '---'
                    tai = '---'
                    status = 'Chờ chuyến sau'

                export_rows.append({
                    'Mã Đơn Gốc': str(r.get('MaDonGoc') or r.get('MaDon', '')),
                    'Mã Kiện': str(r.get('MaKien', '')),
                    'Khách Hàng': str(r.get('ClientName') or r.get('TenKhachHang', '')),
                    'Trạng Thái': str(r.get('TrangThai', '')),
                    'Kho Lấy': str(r.get('KhoLay', '')),
                    'Kho Hiện Tại': str(r.get('KhoHienTai', '')),
                    'Kho Giao': str(r.get('KhoGiao', '')),
                    'Tỉnh Nhận': prov,
                    'KL Tính Cước (KG)': r.get('KG', 0.0),
                    'Cân Nặng Thực Tế (KG)': r.get('CanNangThucTe_Kg', ''),
                    'KL Quy Đổi (KG)': r.get('CanNangQuyDoi_Kg', ''),
                    'Tuyến Xe Dự Kiến': tuyen,
                    'Giờ Xuất Bến': gio,
                    'Điểm Xuất Phát': diem,
                    'Tải Xe (KG)': tai,
                    'Trạng Thái Tuyến': status,
                    'Thời Gian Quét': now_str
                })

            df_export = pd.DataFrame(export_rows)

            # Ensure Tab exists
            meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheet_id = None
            for s in meta.get('sheets', []):
                if s['properties']['title'] == tab_name:
                    sheet_id = s['properties']['sheetId']
                    break

            if sheet_id is None:
                add_req = {
                    'requests': [{
                        'addSheet': {
                            'properties': {
                                'title': tab_name,
                                'gridProperties': {'rowCount': max(len(df_export) + 100, 500), 'columnCount': 20}
                            }
                        }
                    }]
                }
                res_add = service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=add_req).execute()
                sheet_id = res_add['replies'][0]['addSheet']['properties']['sheetId']

            # Clear old content
            service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=f"{tab_name}!A:Q"
            ).execute()

            # Upload new rows
            header = df_export.columns.tolist()
            data_values = [header] + df_export.fillna('').astype(str).values.tolist()

            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{tab_name}!A1",
                valueInputOption='USER_ENTERED',
                body={'values': data_values}
            ).execute()

            direct_link = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={sheet_id}"
            print(f"✅ Đã đồng bộ {len(df_export)} dòng lên Google Sheet: {direct_link}")
            return direct_link

        except Exception as e:
            print(f"⚠️ Chưa thể ghi vào Google Sheet ({e}). Vui lòng chạy auth_google_write.bat để cấp quyền ghi.")
            return self.gg_sheet_url

    def process_and_report(self, target_chat_id=None, target_thread_id=None, send_tele=True, window_hours=4):
        now = get_vietnam_now()
        now_str = now.strftime('%H:%M %d/%m/%Y')
        curr_time_str = now.strftime('%H:%M')
        window_end = now + timedelta(hours=window_hours)
        end_time_str = window_end.strftime('%H:%M')

        chat_dst = target_chat_id or self.chat_id
        if target_thread_id is not None:
            thread_dst = target_thread_id
        elif str(chat_dst) == str(self.chat_id):
            thread_dst = self.thread_id
        else:
            thread_dst = None

        print(f"[{now_str}] Đang quét đơn tồn ({curr_time_str} ➔ {end_time_str}, khung {window_hours}h)...")

        try:
            df, source_desc = self.fetch_live_data()
        except Exception as e:
            err_msg = (
                f"⚠️ <b>LỖI KẾT NỐI DỮ LIỆU TỒN:</b>\n"
                f"Chi tiết: <code>{str(e)}</code>\n\n"
                f"👉 <i>Vui lòng kiểm tra lại kết nối mạng hoặc file cấu hình!</i>"
            )
            print(err_msg)
            if send_tele:
                self.send_telegram(err_msg, chat_id=chat_dst, thread_id=thread_dst)
            return None

        # Extract KG column (support both comma and dot decimal separators)
        for col in ['KL_TinhCuoc_Kg', 'CanNangThucTe_Kg', 'CanNangQuyDoi_Kg']:
            if col in df.columns:
                df['KG'] = pd.to_numeric(df[col].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
                break
        if 'KG' not in df.columns:
            df['KG'] = 0.0

        # Filter transit orders where KhoHienTai is strictly Dai Tu
        if 'KhoHienTai' in df.columns:
            df_daitu = df[df['KhoHienTai'].str.contains('Đài Tư|Dai Tu', case=False, na=False)].copy()
        else:
            df_daitu = df.copy()

        total_orders = len(df_daitu)
        total_kg = df_daitu['KG'].sum()

        if 'KhoGiao' in df_daitu.columns and 'KhoHienTai' in df_daitu.columns:
            df_transit = df_daitu[df_daitu['KhoGiao'] != df_daitu['KhoHienTai']].copy()
        else:
            df_transit = df_daitu.copy()

        transit_count = len(df_transit)
        transit_kg = df_transit['KG'].sum()

        # Extract Province for each order
        df_transit['Tinh'] = df_transit['KhoGiao'].apply(extract_province)

        # Get trips departing in the next window_hours (mặc định 4 giờ tới)
        upcoming_trips = self.get_upcoming_trips(now, window_hours=window_hours)
        print(f"Tìm thấy {len(upcoming_trips)} chuyến xe xuất bến trong khung giờ {curr_time_str} - {end_time_str} ({window_hours} giờ tới).")

        # Map each province to its upcoming trips (bỏ qua Hà Nội và Bắc Ninh)
        prov_to_trips = defaultdict(list)
        for t in upcoming_trips:
            for p in t['ProvincesServed']:
                if not is_no_route_province(p):
                    prov_to_trips[p].append(t)

        # Summary by Province (TOÀN BỘ CÁC TỈNH CÓ HÀNG TỒN)
        if not df_transit.empty:
            prov_summary = df_transit.groupby('Tinh').agg(
                SoDon=('KhoGiao', 'count'),
                TongKG=('KG', 'sum')
            ).reset_index().sort_values('TongKG', ascending=False)
        else:
            prov_summary = pd.DataFrame(columns=['Tinh', 'SoDon', 'TongKG'])

        # Upcoming trips with matching backlog (loại trừ hàng Hà Nội & Bắc Ninh khỏi việc ghép tuyến xe)
        df_transit_route = df_transit[~df_transit['Tinh'].apply(is_no_route_province)]
        seen_trips = set()
        unique_upcoming = []
        for t in upcoming_trips:
            matched = df_transit_route[df_transit_route['Tinh'].isin(t['ProvincesServed'])]
            if not matched.empty and t['MaChuyen'] not in seen_trips:
                seen_trips.add(t['MaChuyen'])
                unique_upcoming.append({
                    'MaTuyen': t['MaTuyen'],
                    'HHMM': t['HHMM'],
                    'TrongTai': t.get('TrongTai', 0),
                    'Orders': len(matched),
                    'KG': matched['KG'].sum(),
                    'Provinces': sorted(list(set(matched['Tinh'])))
                })
        unique_upcoming.sort(key=lambda x: x['HHMM'])

        # Format Telegram Message as requested
        lines = []
        lines.append(f"🚨 <b>CẢNH BÁO TỒN KHO & LỊCH TẢI TUYẾN ({window_hours} GIỜ TỚI)</b>")
        lines.append(f"⏰ Thời điểm quét: <b>{now_str}</b>")
        lines.append(f"⏳ Khung giờ xuất bến: <b>{curr_time_str} ➔ {end_time_str}</b>")
        ex_info = f" <i>(đã loại {self.last_excluded_count} đơn đã xuất kho)</i>" if getattr(self, 'last_excluded_count', 0) > 0 else ""
        lines.append(f"📦 Tổng tồn Đài Tư: <b>{total_orders:,} đơn</b> · <b>{total_kg:,.1f} kg</b>{ex_info}")
        lines.append(f"🚚 Hàng cần đi các tỉnh: <b>{transit_count:,} đơn</b> · <b>{transit_kg:,.1f} kg</b>\n")

        if prov_summary.empty:
            lines.append("🎉 <i>Hiện không có hàng tồn cần trung chuyển đi các tỉnh!</i>\n")
        else:
            lines.append(f"📍 <b>CHI TIẾT TOÀN BỘ CÁC TỈNH CÓ HÀNG TỒN ({len(prov_summary)} TỈNH):</b>")
            for idx, r in enumerate(prov_summary.itertuples(), 1):
                p = r.Tinh
                sd = r.SoDon
                kg = r.TongKG
                if is_no_route_province(p):
                    # Riêng Hà Nội và Bắc Ninh: chỉ liệt kê vol hàng tồn, không định hướng tuyến
                    lines.append(f"{idx}. <b>{p}:</b> {sd} đơn · {kg:,.1f} kg")
                else:
                    trips = prov_to_trips.get(p, [])
                    if trips:
                        t0 = trips[0]
                        trip_info = f"🚛 <code>{t0['MaTuyen']}</code> (<b>{t0['HHMM']}</b>)"
                    else:
                        trip_info = f"⏳ <i>Chưa có chuyến trong {window_hours}h</i>"
                    lines.append(f"{idx}. <b>{p}:</b> {sd} đơn · {kg:,.1f} kg ➔ {trip_info}")
            lines.append("")

        if unique_upcoming:
            lines.append(f"🚛 <b>LỊCH CÁC TUYẾN XE XUẤT BẾN TRONG {window_hours} GIỜ TỚI (CÓ HÀNG ĐI ĐƯỢC):</b>")
            for u in unique_upcoming:
                tt = f"{u['TrongTai']:,} kg" if u['TrongTai'] else "cố định"
                p_str = ', '.join(u['Provinces'])
                lines.append(f"• <b>{u['HHMM']}</b> — <code>{u['MaTuyen']}</code> (Tải: {tt}): <b>{u['Orders']} đơn · {u['KG']:,.1f} kg</b> (Đi: {p_str})")
            lines.append("")
        else:
            lines.append(f"ℹ️ <i>Trong {window_hours} giờ tới không có chuyến xe nào xuất bến khớp với các tỉnh có hàng tồn.</i>\n")

        # Add Google Sheet detail link
        sheet_link = self.gg_sheet_url or "https://docs.google.com/spreadsheets/d/1YNuLmUv6FRVMieyQy4JVnFscvkqnBdygzaWaQvOWMzU/edit?gid=654306746#gid=654306746"
        lines.append(f"📊 <b>Dữ liệu chi tiết {transit_count:,} đơn tồn (Google Sheet Tab TonUpdate1h):</b>")
        lines.append(f'👉 <a href="{sheet_link}">Bấm vào đây để xem chi tiết từng đơn</a>\n')
        lines.append("👉 <i>Vui lòng ưu tiên gom và xếp hàng lên các chuyến xe có giờ xuất bến sớm nhất!</i>")
        msg = "\n".join(lines)

        print("\n" + "=" * 70)
        print(msg)
        print("=" * 70 + "\n")

        if send_tele:
            self.send_telegram(msg, chat_id=chat_dst, thread_id=thread_dst)

        return msg

    def send_telegram(self, text, chat_id=None, thread_id=None):
        dst_chat = chat_id or self.chat_id
        if thread_id is not None:
            dst_thread = thread_id
        elif str(dst_chat) == str(self.chat_id):
            dst_thread = self.thread_id
        else:
            dst_thread = None

        if not self.bot_token or not dst_chat:
            print("Telegram Token/Chat ID chưa được cấu hình. Bỏ qua gửi tin.")
            return

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        # Split message into chunks <= 3500 chars to avoid Telegram 4096 limit
        chunks = []
        if len(text) <= 3500:
            chunks = [text]
        else:
            current_chunk = []
            curr_len = 0
            for line in text.split('\n'):
                if curr_len + len(line) + 1 > 3500:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = [line]
                    curr_len = len(line)
                else:
                    current_chunk.append(line)
                    curr_len += len(line) + 1
            if current_chunk:
                chunks.append('\n'.join(current_chunk))

        for idx, chunk in enumerate(chunks, 1):
            payload = {
                "chat_id": dst_chat,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }
            if dst_thread:
                payload["message_thread_id"] = dst_thread
            try:
                r = requests.post(url, json=payload, timeout=15)
                r.raise_for_status()
                target_desc = f"Topic {dst_thread}" if dst_thread else f"Chat {dst_chat}"
                print(f"✅ Đã gửi phần {idx}/{len(chunks)} lên Telegram {target_desc} thành công!")
            except Exception as e:
                err_detail = ""
                try:
                    if 'r' in locals() and hasattr(r, 'text'):
                        err_detail = f" - Response: {r.text}"
                except Exception:
                    pass
                print(f"❌ Lỗi gửi Telegram phần {idx}: {e}{err_detail}")

    def register_commands(self):
        url = f"https://api.telegram.org/bot{self.bot_token}/setMyCommands"
        commands = [
            {'command': 'ton', 'description': 'Lấy cảnh báo hàng tồn & lịch tải tuyến 4 giờ tới'},
            {'command': 'check', 'description': 'Kiểm tra lịch xe xuất bến gần nhất (4 giờ tới)'},
            {'command': 'status', 'description': 'Kiểm tra trạng thái hoạt động trực tuyến 24/7 của Bot'},
            {'command': 'login', 'description': 'Đăng nhập Metabase tự động vĩnh viễn (/login <email> <mk>)'},
            {'command': 'token', 'description': 'Cập nhật session token Metabase thủ công (/token <id>)'},
            {'command': 'sheet', 'description': 'Cập nhật link Google Sheet (/sheet <link>)'},
            {'command': 'help', 'description': 'Hướng dẫn sử dụng bot'}
        ]
        try:
            r = requests.post(url, json={'commands': commands}, timeout=10)
            if r.json().get('ok'):
                print("✅ Đã đăng ký danh sách lệnh Bot Telegram thành công.")
        except Exception as e:
            print(f"Lỗi đăng ký lệnh Telegram: {e}")

    def handle_telegram_update(self, update):
        message = update.get('message') or update.get('channel_post')
        if not message:
            return

        text = (message.get('text') or '').strip()
        chat = message.get('chat', {})
        chat_id = chat.get('id')
        thread_id = message.get('message_thread_id')
        sender = message.get('from', {})
        sender_name = sender.get('first_name', 'bạn')

        if not text:
            return

        print(f"📩 Nhận tin nhắn từ {sender_name} (chat={chat_id}, thread={thread_id}): {text}")

        # Send typing indicator
        try:
            action_payload = {'chat_id': chat_id, 'action': 'typing'}
            if thread_id:
                action_payload['message_thread_id'] = thread_id
            requests.post(f"https://api.telegram.org/bot{self.bot_token}/sendChatAction", json=action_payload, timeout=5)
        except Exception:
            pass

        # 1. Help / Start
        if text.startswith('/start') or text.startswith('/help'):
            help_msg = (
                f"👋 Chào <b>{sender_name}</b>! Tôi là Bot Cảnh Báo Tồn B2B & Lịch Xe GHN.\n\n"
                f"🛠 <b>CÁC LỆNH HỖ TRỢ:</b>\n"
                f"• Gõ <code>/ton</code> hoặc <code>/check</code>: Quét tồn và báo cáo lịch tải tuyến 4 giờ tới.\n"
                f"• Gõ <code>/login &lt;email&gt; &lt;mật_khẩu&gt;</code>: <b>Tự động đăng nhập Metabase</b> — Bot sẽ tự động lấy và gia hạn token mới vĩnh viễn, không bao giờ lo hết hạn token! <i>(Nên chat riêng với Bot để bảo mật mật khẩu)</i>.\n"
                f"• Gõ <code>/token &lt;session_token&gt;</code>: Cập nhật mã Cookie <code>metabase.SESSION</code> mới khi phiên hết hạn.\n"
                f"• Gõ <code>/sheet &lt;link_ggsheet&gt;</code>: Cập nhật đường link Google Sheet chi tiết.\n"
                f"• Bạn cũng có thể tag <code>@CanhBaoHangVeGXT_Bot</code> hoặc gõ tin nhắn chứa từ khóa 'báo tồn', 'check tồn' trong topic.\n\n"
                f"📋 <b>Link Google Sheet hiện tại:</b>\n<a href=\"{self.gg_sheet_url}\">{self.gg_sheet_url}</a>"
            )
            self.send_telegram(help_msg, chat_id=chat_id, thread_id=thread_id)
            return

        # 2. Metabase Auto-login: /login <username> <password>
        if text.startswith('/login'):
            parts = text.split(maxsplit=2)
            if len(parts) < 3 or not parts[1].strip() or not parts[2].strip():
                usage_msg = (
                    "⚠️ <b>Cú pháp lệnh đăng nhập chưa đúng!</b>\n"
                    "Vui lòng gửi theo cú pháp: <code>/login &lt;email_metabase&gt; &lt;mật_khẩu&gt;</code>\n\n"
                    "<i>Ví dụ:</i>\n"
                    "<code>/login khanhnd@ghn.vn MatKhauCuaBan123</code>\n\n"
                    "🔒 <b>Lưu ý bảo mật:</b> Bạn nên gửi lệnh này trong <b>tin nhắn riêng trực tiếp với Bot (@CanhBaoHangVeGXT_Bot)</b> thay vì trong nhóm chat để bảo mật mật khẩu!"
                )
                self.send_telegram(usage_msg, chat_id=chat_id, thread_id=thread_id)
                return

            uname = parts[1].strip()
            pword = parts[2].strip()

            # Attempt auto-login
            ok, res_msg = self.login_metabase(username=uname, password=pword)

            # Try deleting user's message to avoid leaving password visible in chat
            try:
                msg_id = message.get('message_id')
                if msg_id:
                    requests.post(f"https://api.telegram.org/bot{self.bot_token}/deleteMessage", json={'chat_id': chat_id, 'message_id': msg_id}, timeout=5)
            except Exception:
                pass

            if ok:
                success_msg = (
                    f"🎉 <b>ĐĂNG NHẬP METABASE THÀNH CÔNG!</b>\n\n"
                    f"👤 Tài khoản: <code>{uname}</code>\n"
                    f"🔑 Session ID cấp mới: <code>{self.session_token[:8]}***</code>\n\n"
                    f"✅ <b>Từ bây giờ Bot sẽ tự động gia hạn token vĩnh viễn!</b>\n"
                    f"Mỗi khi phiên làm việc hết hạn, bot sẽ tự động đăng nhập lại để cấp token mới trong 1 giây mà bạn không cần phải copy cookie thủ công nữa.\n\n"
                    f"👉 Bây giờ bạn có thể gõ <code>/ton</code> để lấy báo cáo ngay!"
                )
                self.send_telegram(success_msg, chat_id=chat_id, thread_id=thread_id)
            else:
                fail_msg = (
                    f"❌ <b>Đăng nhập Metabase thất bại!</b>\n\n"
                    f"👤 Tài khoản: <code>{uname}</code>\n"
                    f"⚠️ Chi tiết lỗi từ Metabase: <code>{res_msg}</code>\n\n"
                    f"👉 Vui lòng kiểm tra lại email hoặc mật khẩu tài khoản Metabase của bạn.\n"
                    f"💡 <i>Nếu tài khoản của bạn chỉ đăng nhập qua nút Google SSO:</i> Bạn hãy truy cập vào <a href=\"https://data-bi.ghn.vn/auth/forgot_password\">https://data-bi.ghn.vn/auth/forgot_password</a> để tạo mật khẩu riêng cho email GHN của bạn."
                )
                self.send_telegram(fail_msg, chat_id=chat_id, thread_id=thread_id)
            return

        # 3. Update Metabase Session Token: /token <new_token>
        if text.startswith('/token'):
            parts = text.split(maxsplit=1)
            if len(parts) < 2 or not parts[1].strip():
                usage_msg = (
                    "⚠️ <b>Cú pháp chưa đúng!</b>\n"
                    "Vui lòng gửi theo cú pháp: <code>/token &lt;mã_metabase.SESSION_mới&gt;</code>\n\n"
                    "<i>Ví dụ:</i>\n"
                    "<code>/token 911df869-0b66-4af3-a701-a10a563c33ad</code>"
                )
                self.send_telegram(usage_msg, chat_id=chat_id, thread_id=thread_id)
                return

            new_token = parts[1].strip()
            old_token = self.session_token
            self.session_token = new_token
            try:
                test_df = self.fetch_live_metabase()
                self.save_config()
                success_msg = (
                    f"✅ <b>Cập nhật Session Metabase thành công!</b>\n"
                    f"Kết nối thành công tới Card {self.card_id} (tìm thấy {len(test_df):,} dòng đơn tồn).\n\n"
                    f"👉 Bây giờ bạn có thể gõ <code>/ton</code> để lấy báo cáo ngay!"
                )
                self.send_telegram(success_msg, chat_id=chat_id, thread_id=thread_id)
            except Exception as e:
                self.session_token = old_token # revert on fail
                err_msg = (
                    f"❌ <b>Token mới không kết nối được Metabase:</b>\n"
                    f"Chi tiết: <code>{str(e)}</code>\n\n"
                    f"👉 Vui lòng kiểm tra lại giá trị cookie <code>metabase.SESSION</code> từ trình duyệt."
                )
                self.send_telegram(err_msg, chat_id=chat_id, thread_id=thread_id)
            return

        # 3. Update Google Sheet URL: /sheet <link>
        if text.startswith('/sheet'):
            parts = text.split(maxsplit=1)
            if len(parts) < 2 or not parts[1].strip():
                cur_msg = (
                    f"📋 <b>Link Google Sheet chi tiết hiện tại:</b>\n"
                    f"<a href=\"{self.gg_sheet_url}\">{self.gg_sheet_url}</a>\n\n"
                    f"👉 Để đổi link mới, vui lòng gửi: <code>/sheet &lt;đường_link_mới&gt;</code>"
                )
                self.send_telegram(cur_msg, chat_id=chat_id, thread_id=thread_id)
                return

            new_url = parts[1].strip()
            self.gg_sheet_url = new_url
            self.save_config()
            confirm_msg = (
                f"✅ <b>Đã cập nhật link Google Sheet chi tiết!</b>\n"
                f"Link mới: <a href=\"{new_url}\">{new_url}</a>"
            )
            self.send_telegram(confirm_msg, chat_id=chat_id, thread_id=thread_id)
            return

        # 4. Status / Ping
        if text.startswith('/status') or text.startswith('/ping'):
            now = get_vietnam_now()
            status_msg = (
                f"🤖 <b>BOT CẢNH BÁO TỒN B2B ĐANG ONLINE 24/7!</b>\n\n"
                f"⏰ Giờ hệ thống: <b>{now.strftime('%H:%M:%S %d/%m/%Y')}</b> (Giờ VN)\n"
                f"📊 Nguồn tồn chính: Google Sheet tab <code>TonUpdate1h</code>\n"
                f"🚚 Cửa sổ quét xe: <b>4 giờ tới</b>\n"
                f"🎯 Nhóm báo mặc định: Topic <code>{self.thread_id}</code>\n\n"
                f"👉 Gõ <code>/ton</code> hoặc <code>/check</code> để lấy báo cáo ngay!"
            )
            self.send_telegram(status_msg, chat_id=chat_id, thread_id=thread_id)
            return

        # 5. Trigger Report: /ton, /check, /baocao, mention bot, or keywords
        is_command = text.startswith('/ton') or text.startswith('/check') or text.startswith('/baocao')
        is_mention = '@CanhBaoHangVeGXT_Bot' in text or 'CanhBaoHangVeGXT_Bot' in text
        lower_text = text.lower()
        is_keyword = any(k in lower_text for k in [
            'báo tồn', 'check tồn', 'lịch xe', 'hàng tồn', 'xem tồn', 'báo cáo tồn',
            'kiem tra ton', 'bao ton', 'xem ton', 'lich xe', 'ton', 'tồn', 'check'
        ])
        is_private = chat.get('type') == 'private'

        # Match command, mention, private chat with keyword, or topic with keyword
        if is_command or is_mention or (is_private and is_keyword) or (str(thread_id) == str(self.thread_id) and is_keyword):
            self.process_and_report(target_chat_id=chat_id, target_thread_id=thread_id, send_tele=True)
            return

        # Fallback for 1-on-1 private chat if message was not recognized
        if is_private:
            fallback_msg = (
                f"👋 Chào <b>{sender_name}</b>!\n\n"
                f"Tôi đã nhận được tin nhắn: <i>\"{text}\"</i>\n\n"
                f"👉 Để lấy báo cáo chi tiết toàn bộ các tỉnh tồn & lịch xuất bến trong 4 giờ tới, bạn hãy gửi lệnh:\n"
                f"• <code>/ton</code> hoặc <code>/check</code>\n\n"
                f"ℹ️ Gõ <code>/help</code> để xem hướng dẫn đầy đủ các lệnh."
            )
            self.send_telegram(fallback_msg, chat_id=chat_id, thread_id=thread_id)

    def run_listener(self):
        port = os.environ.get('PORT')
        if port:
            start_health_server(int(port))
        print("🚀 Bắt đầu lắng nghe tin nhắn Telegram (Chế độ gọi bot mới báo)...")
        self.register_commands()
        offset = None

        while True:
            try:
                params = {'timeout': 25}
                if offset:
                    params['offset'] = offset

                url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
                res = requests.get(url, params=params, timeout=35)
                if res.status_code != 200:
                    print(f"⚠️ Telegram polling status {res.status_code}: {res.text}")
                    time.sleep(3)
                    continue

                data = res.json()
                if not data.get('ok'):
                    print(f"⚠️ Telegram getUpdates not ok: {data}")
                    time.sleep(3)
                    continue

                for update in data.get('result', []):
                    offset = update['update_id'] + 1
                    self.handle_telegram_update(update)


            except requests.exceptions.Timeout:
                continue
            except Exception as e:
                print(f"Lỗi polling listener: {e}")
                time.sleep(3)

    def run_daemon(self, interval_seconds=3600):
        print(f"🚀 Bắt đầu chạy ngầm tự động mỗi {interval_seconds // 60} phút...")
        while True:
            try:
                self.process_and_report(send_tele=True)
            except Exception as e:
                print(f"Lỗi trong vòng lặp daemon: {e}")
            print(f"Đang chờ {interval_seconds // 60} phút cho lần quét tiếp theo...")
            time.sleep(interval_seconds)

if __name__ == '__main__':
    advisor = B2BTonAdvisor()

    if '--listen' in sys.argv or '--bot' in sys.argv:
        advisor.run_listener()
    elif '--daemon' in sys.argv:
        advisor.run_daemon(interval_seconds=3600)
    else:
        advisor.process_and_report(send_tele=True)
