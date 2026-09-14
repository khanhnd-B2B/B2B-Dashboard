import requests
import json
import pandas as pd
import re
import os
import sys
import time
from datetime import datetime, timedelta
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'advisor_config.json')

DEFAULT_CONFIG = {
    'metabase_url': 'https://data-bi.ghn.vn',
    'metabase_session': '911df869-0b66-4af3-a701-a10a563c33ad',
    'metabase_card_id': 6287,
    'telegram_bot_token': '8370307476:AAEsPB2UZ0zQHMTEWPGFFBw7fUYuWsePxPM',
    'telegram_chat_id': '-1004492922071',
    'telegram_message_thread_id': 7090,
    'gg_sheet_url': 'https://docs.google.com/spreadsheets/d/1YNuLmUv6FRVMieyQy4JVnFscvkqnBdygzaWaQvOWMzU/edit'
}

TRUCK_FILE = os.path.join(os.path.dirname(__file__), 'data chuyến Truck 7 ngày 11.09.xlsx')

PREFIX_TO_PROVINCE = {
    'HNO': 'Hà Nội', 'HN': 'Hà Nội',
    'QNI': 'Quảng Ninh', 'QN': 'Quảng Ninh',
    'BGI': 'Bắc Giang', 'BG': 'Bắc Giang',
    'BNI': 'Bắc Ninh', 'BN': 'Bắc Ninh',
    'THO': 'Thanh Hóa', 'TH': 'Thanh Hóa',
    'NAN': 'Nghệ An', 'NA': 'Nghệ An',
    'HPG': 'Hải Phòng', 'HP': 'Hải Phòng', 'HPH': 'Hải Phòng',
    'HDU': 'Hải Dương', 'HD': 'Hải Dương',
    'HYE': 'Hưng Yên', 'HY': 'Hưng Yên',
    'NDI': 'Nam Định', 'NĐ': 'Nam Định',
    'NBI': 'Ninh Bình', 'NB': 'Ninh Bình',
    'TBH': 'Thái Bình', 'TB': 'Thái Bình', 'TBI': 'Thái Bình',
    'HNA': 'Hà Nam', 'HNAM': 'Hà Nam',
    'THN': 'Thái Nguyên', 'TN': 'Thái Nguyên',
    'LSN': 'Lạng Sơn', 'LS': 'Lạng Sơn', 'LSO': 'Lạng Sơn',
    'PTO': 'Phú Thọ', 'PT': 'Phú Thọ', 'PTH': 'Phú Thọ',
    'VPH': 'Vĩnh Phúc', 'VP': 'Vĩnh Phúc',
    'HBI': 'Hòa Bình', 'HB': 'Hòa Bình',
    'SLA': 'Sơn La', 'SL': 'Sơn La',
    'LCA': 'Lào Cai', 'LC': 'Lào Cai',
    'YBA': 'Yên Bái', 'YB': 'Yên Bái',
    'TQG': 'Tuyên Quang', 'TQ': 'Tuyên Quang',
    'HAG': 'Hà Giang', 'HG': 'Hà Giang',
    'DNA': 'Đà Nẵng', 'ĐN': 'Đà Nẵng', 'DNG': 'Đà Nẵng',
    'SGN': 'Hồ Chí Minh', 'HCM': 'Hồ Chí Minh',
    'BDU': 'Bình Dương', 'BD': 'Bình Dương',
    'DNI': 'Đồng Nai', 'ĐNAI': 'Đồng Nai',
    'LAN': 'Long An', 'LA': 'Long An',
    'BPC': 'Bình Phước', 'BP': 'Bình Phước', 'BPH': 'Bình Phước',
    'BTH': 'Bình Thuận', 'BT': 'Bình Thuận', 'NTH': 'Ninh Thuận',
    'QBI': 'Quảng Bình', 'QB': 'Quảng Bình',
    'QTI': 'Quảng Trị', 'QT': 'Quảng Trị', 'QTR': 'Quảng Trị',
    'TTH': 'Thừa Thiên Huế', 'HUE': 'Thừa Thiên Huế',
    'QNA': 'Quảng Nam', 'QNM': 'Quảng Nam',
    'QNG': 'Quảng Ngãi', 'QNGA': 'Quảng Ngãi',
    'BDI': 'Bình Định', 'BĐ': 'Bình Định',
    'PYE': 'Phú Yên', 'PY': 'Phú Yên',
    'KHA': 'Khánh Hòa', 'KH': 'Khánh Hòa',
    'GLI': 'Gia Lai', 'GL': 'Gia Lai',
    'DKL': 'Đắk Lắk', 'DLK': 'Đắk Lắk',
    'DKN': 'Đắk Nông', 'DNO': 'Đắk Nông',
    'LDG': 'Lâm Đồng', 'LĐ': 'Lâm Đồng',
    'CTO': 'Cần Thơ', 'CT': 'Cần Thơ',
    'KGG': 'Kiên Giang', 'KG': 'Kiên Giang', 'KGI': 'Kiên Giang',
    'AGG': 'An Giang', 'AG': 'An Giang',
    'CMU': 'Cà Mau', 'CM': 'Cà Mau',
    'BKA': 'Bắc Kạn', 'DBI': 'Điện Biên',
    'STR': 'Sóc Trăng', 'TNI': 'Tây Ninh',
    'KTU': 'Kon Tum', 'CBA': 'Cao Bằng',
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
    'BRVT', 'Đồng Tháp', 'Trà Vinh', 'Ninh Thuận', 'Tây Ninh'
]

def extract_province(name):
    name = str(name).strip()
    m = re.match(r'^\(([A-Za-z0-9]+)\)', name)
    if m:
        pfx = m.group(1).upper()
        if pfx in PREFIX_TO_PROVINCE:
            return PREFIX_TO_PROVINCE[pfx]

    parts = name.split('-')
    if len(parts) >= 2:
        last_part = parts[-1].strip()
        for p in PROVINCES_LIST:
            if p.lower() == last_part.lower():
                if 'thanh ho' in p.lower(): return 'Thanh Hóa'
                if 'hoà bình' in p.lower() or 'hòa bình' in p.lower(): return 'Hòa Bình'
                if 'khánh ho' in p.lower(): return 'Khánh Hòa'
                if 'brvt' in p.lower() or 'vũng tàu' in p.lower(): return 'Bà Rịa - Vũng Tàu'
                if p == 'HCM': return 'Hồ Chí Minh'
                return p

    for p in PROVINCES_LIST:
        if p.lower() in name.lower():
            if 'thanh ho' in p.lower(): return 'Thanh Hóa'
            if 'hoà bình' in p.lower() or 'hòa bình' in p.lower(): return 'Hòa Bình'
            if 'khánh ho' in p.lower(): return 'Khánh Hòa'
            if 'brvt' in p.lower() or 'vũng tàu' in p.lower(): return 'Bà Rịa - Vũng Tàu'
            if p == 'HCM': return 'Hồ Chí Minh'
            return p

    if any(k in name.lower() for k in ['hà nội', 'long biên', 'thanh xuân', 'hoài đức', 'cầu giấy', 'ba đình', 'đông anh', 'mê linh', 'sóc sơn', 'tây hồ', 'hoàn kiếm', 'đống đa', 'hai bà trưng', 'thanh trì', 'hoàng mai', 'hà đông', 'nam từ liêm', 'bắc từ liêm']):
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

        # Allow environment overrides
        self.metabase_url = os.environ.get('METABASE_URL', cfg['metabase_url'])
        self.session_token = os.environ.get('METABASE_SESSION', cfg['metabase_session'])
        self.card_id = int(os.environ.get('METABASE_CARD_ID', cfg['metabase_card_id']))
        self.bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', cfg['telegram_bot_token'])
        self.chat_id = os.environ.get('TELEGRAM_CHAT_ID', cfg['telegram_chat_id'])
        self.thread_id = int(os.environ.get('TELEGRAM_MESSAGE_THREAD_ID', cfg.get('telegram_message_thread_id', 7090)))
        self.gg_sheet_url = os.environ.get('GG_SHEET_URL', cfg.get('gg_sheet_url', ''))

    def save_config(self):
        cfg = {
            'metabase_url': self.metabase_url,
            'metabase_session': self.session_token,
            'metabase_card_id': self.card_id,
            'telegram_bot_token': self.bot_token,
            'telegram_chat_id': self.chat_id,
            'telegram_message_thread_id': self.thread_id,
            'gg_sheet_url': self.gg_sheet_url
        }
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

    def fetch_live_metabase(self):
        url = f'{self.metabase_url}/api/card/{self.card_id}/query/json'
        headers = {
            'X-Metabase-Session': self.session_token,
            'Cookie': f'metabase.SESSION={self.session_token}',
            'Content-Type': 'application/json'
        }
        res = requests.post(url, headers=headers, json={}, timeout=40)
        res.raise_for_status()
        return pd.DataFrame(res.json())

    def get_upcoming_trips_in_90min(self, current_time):
        if self.df_truck is None:
            return []

        curr_time_str = current_time.strftime('%H:%M')
        window_end = current_time + timedelta(minutes=90) # 1h 30p window
        end_time_str = window_end.strftime('%H:%M')

        # Filter stop 1 in the 1h30m window
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

    def process_and_report(self, target_chat_id=None, target_thread_id=None, send_tele=True):
        now = datetime.now()
        now_str = now.strftime('%H:%M %d/%m/%Y')
        curr_time_str = now.strftime('%H:%M')
        window_end = now + timedelta(minutes=90)
        end_time_str = window_end.strftime('%H:%M')

        chat_dst = target_chat_id or self.chat_id
        thread_dst = target_thread_id if target_thread_id is not None else self.thread_id

        print(f"[{now_str}] Đang quét đơn tồn Metabase & Lịch xe trong vòng 1h30p ({curr_time_str} ➔ {end_time_str})...")

        try:
            df = self.fetch_live_metabase()
        except Exception as e:
            err_msg = (
                f"⚠️ <b>LỖI KẾT NỐI METABASE (Card {self.card_id}):</b>\n"
                f"Chi tiết: <code>{str(e)}</code>\n\n"
                f"🔑 <b>Phiên đăng nhập (Session) có thể đã hết hạn!</b>\n"
                f"👉 <i>Vui lòng cập nhật token mới bằng lệnh:</i>\n"
                f"<code>/token &lt;session_token_mới&gt;</code>"
            )
            print(err_msg)
            if send_tele:
                self.send_telegram(err_msg, chat_id=chat_dst, thread_id=thread_dst)
            return None

        total_orders = len(df)

        # Extract KG column
        for col in ['KL_TinhCuoc_Kg', 'CanNangThucTe_Kg', 'CanNangQuyDoi_Kg']:
            if col in df.columns:
                df['KG'] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                break
        if 'KG' not in df.columns:
            df['KG'] = 0.0

        total_kg = df['KG'].sum()

        # Filter transit orders where KhoHienTai is strictly Dai Tu
        df_transit = df[(df['KhoGiao'] != df['KhoHienTai']) & (df['KhoHienTai'].str.contains('Đài Tư|Dai Tu', case=False, na=False))].copy()
        transit_count = len(df_transit)
        transit_kg = df_transit['KG'].sum()

        # Extract Province for each order
        df_transit['Tinh'] = df_transit['KhoGiao'].apply(extract_province)

        # Get trips departing in the next 1 hour 30 minutes
        upcoming_trips = self.get_upcoming_trips_in_90min(now)
        print(f"Tìm thấy {len(upcoming_trips)} chuyến xe xuất bến trong khung giờ {curr_time_str} - {end_time_str}.")

        def get_mins_diff(hhmm, current_dt):
            h, m = map(int, hhmm.split(':'))
            target = current_dt.replace(hour=h, minute=m, second=0, microsecond=0)
            if (target - current_dt).total_seconds() < -1800:
                target += timedelta(days=1)
            return (target - current_dt).total_seconds() / 60

        route_reports = []
        for tdata in upcoming_trips:
            provinces_served = tdata['ProvincesServed']
            matched_backlog = df_transit[df_transit['Tinh'].isin(provinces_served)].copy()
            if matched_backlog.empty:
                continue

            # Group by Province only
            prov_data = {}
            for prov in sorted(list(provinces_served)):
                p_orders = matched_backlog[matched_backlog['Tinh'] == prov]
                if p_orders.empty:
                    continue

                prov_data[prov] = {
                    'SoDon': int(p_orders['KhoGiao'].count()),
                    'TongKG': float(p_orders['KG'].sum())
                }

            if prov_data:
                total_route_orders = sum(p['SoDon'] for p in prov_data.values())
                total_route_kg = sum(p['TongKG'] for p in prov_data.values())

                route_reports.append({
                    'MaTuyen': tdata['MaTuyen'],
                    'HHMM': tdata['HHMM'],
                    'Origin': tdata['Origin'],
                    'TrongTai': tdata['TrongTai'],
                    'TotalOrders': total_route_orders,
                    'TotalKG': total_route_kg,
                    'Provinces': prov_data,
                    'MinsAway': get_mins_diff(tdata['HHMM'], now)
                })

        # Sort chronologically by minutes until departure, then highest KG
        route_reports.sort(key=lambda x: (x['MinsAway'], -x['TotalKG']))

        # Format Telegram Message as requested
        lines = []
        lines.append("🚨 <b>CẢNH BÁO LỊCH TẢI TUYẾN (1H30P TỚI)</b>")
        lines.append(f"⏰ Thời điểm quét: <b>{now_str}</b>")
        lines.append(f"⏳ Khung giờ xuất bến: <b>{curr_time_str} ➔ {end_time_str}</b>")
        lines.append(f"📦 Tổng tồn Đài Tư: <b>{total_orders:,} đơn</b> · <b>{total_kg:,.1f} kg</b>")
        lines.append(f"🚚 Hàng cần đi các tỉnh: <b>{transit_count:,} đơn</b> · <b>{transit_kg:,.1f} kg</b>\n")

        if not route_reports:
            lines.append("ℹ️ <i>Trong 1h30p tới không có chuyến xe nào xuất bến khớp với các tỉnh có hàng tồn.</i>")
        else:
            lines.append(f"🚛 <b>DANH SÁCH LỊCH TẢI TUYẾN ({len(route_reports)} TUYẾN KHỚP LỊCH):</b>\n")
            # Liệt kê toàn bộ các tuyến, chỉ hiện tuyến xe và tỉnh tồn
            for idx, r in enumerate(route_reports, 1):
                tt_str = f"{r['TrongTai']} kg" if r['TrongTai'] else "Xe cố định"
                lines.append(
                    f"🚛 <b>{idx}. Tuyến <code>{r['MaTuyen']}</code> — Cung giờ: <b>{r['HHMM']}</b></b> (Tải xe: {tt_str})\n"
                    f"   📊 <b>Tổng hàng lên xe: {r['TotalOrders']} đơn · ⚖️ {r['TotalKG']:,.1f} kg</b>"
                )
                for prov_name, pdata in r['Provinces'].items():
                    lines.append(f"   • <b>Tỉnh {prov_name}:</b> {pdata['SoDon']} đơn - {pdata['TongKG']:,.1f} kg")
                lines.append("")

        # Add Google Sheet detail link
        if self.gg_sheet_url:
            lines.append(f"📊 <b>Dữ liệu chi tiết đơn tồn (Google Sheet):</b>\n👉 <a href=\"{self.gg_sheet_url}\">Bấm vào đây để xem chi tiết</a>\n")

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
        dst_thread = thread_id if thread_id is not None else self.thread_id

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
                print(f"❌ Lỗi gửi Telegram phần {idx}: {e}")

    def register_commands(self):
        url = f"https://api.telegram.org/bot{self.bot_token}/setMyCommands"
        commands = [
            {'command': 'ton', 'description': 'Lấy cảnh báo hàng tồn & lịch tải tuyến 1h30p tới'},
            {'command': 'check', 'description': 'Kiểm tra lịch xe xuất bến gần nhất'},
            {'command': 'token', 'description': 'Cập nhật session token Metabase (/token <session_id>)'},
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
                f"• Gõ <code>/ton</code> hoặc <code>/check</code>: Quét tồn Metabase và báo cáo lịch tải tuyến 1h30p tới.\n"
                f"• Gõ <code>/token &lt;session_token&gt;</code>: Cập nhật mã Cookie <code>metabase.SESSION</code> mới khi phiên hết hạn.\n"
                f"• Gõ <code>/sheet &lt;link_ggsheet&gt;</code>: Cập nhật đường link Google Sheet chi tiết.\n"
                f"• Bạn cũng có thể tag <code>@CanhBaoHangVeGXT_Bot</code> hoặc gõ tin nhắn chứa từ khóa 'báo tồn', 'check tồn' trong topic.\n\n"
                f"📋 <b>Link Google Sheet hiện tại:</b>\n<a href=\"{self.gg_sheet_url}\">{self.gg_sheet_url}</a>"
            )
            self.send_telegram(help_msg, chat_id=chat_id, thread_id=thread_id)
            return

        # 2. Update Metabase Session Token: /token <new_token>
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

        # 4. Trigger Report: /ton, /check, /baocao, mention bot, or keywords
        is_command = text.startswith('/ton') or text.startswith('/check') or text.startswith('/baocao')
        is_mention = '@CanhBaoHangVeGXT_Bot' in text or 'CanhBaoHangVeGXT_Bot' in text
        is_keyword = any(k in text.lower() for k in ['báo tồn', 'check tồn', 'lịch xe', 'hàng tồn', 'xem tồn', 'báo cáo tồn'])
        is_private = chat.get('type') == 'private'

        if is_command or is_mention or (is_private and is_keyword) or (thread_id == self.thread_id and is_keyword):
            self.process_and_report(target_chat_id=chat_id, target_thread_id=thread_id, send_tele=True)

    def run_listener(self):
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
                    time.sleep(3)
                    continue

                data = res.json()
                if not data.get('ok'):
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
