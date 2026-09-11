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

# Configuration
METABASE_URL = os.environ.get('METABASE_URL', 'https://data-bi.ghn.vn')
METABASE_SESSION = os.environ.get('METABASE_SESSION', '911df869-0b66-4af3-a701-a10a563c33ad')
CARD_ID = int(os.environ.get('METABASE_CARD_ID', 6287))

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8370307476:AAEsPB2UZ0zQHMTEWPGFFBw7fUYuWsePxPM')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '-1004492922071')

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
    'Kho Trung Chuyển Hà Nội 02',
    'Kho Trung Chuyển Hưng Yên 01',
    'Kho Trung Chuyển Dương Xá'
]

ORIGIN_EXCLUDED_STOPS = {
    'kho b2b - đài tư - hà nội',
    'kho trung chuyển hà nội 02'
}

class B2BTonAdvisor:
    def __init__(self, session_token=METABASE_SESSION):
        self.session_token = session_token
        self._load_truck_data()

    def _load_truck_data(self):
        if not os.path.exists(TRUCK_FILE):
            print(f"Warning: Không tìm thấy file {TRUCK_FILE}")
            self.df_truck = None
            return

        self.df_truck = pd.read_excel(TRUCK_FILE, header=1)
        self.df_truck['GioDuKienDen_GMT7'] = pd.to_datetime(self.df_truck['GioDuKienDen_GMT7'], errors='coerce')
        self.df_truck['HHMM'] = self.df_truck['GioDuKienDen_GMT7'].dt.strftime('%H:%M')

        # Filter trips starting at Đài Tư / HN02 (prioritized)
        stop1 = self.df_truck[self.df_truck['ThuTuDiem'] == 1]
        self.b2b_stop1 = stop1[stop1['TenDiem'].isin(VALID_ORIGINS)].copy()

    def fetch_live_metabase(self):
        url = f'{METABASE_URL}/api/card/{CARD_ID}/query/json'
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
                    provinces_served.update(['Hưng Yên', 'Nam Định', 'Ninh Bình', 'Hải Dương', 'Thái Bình', 'Hà Nam'])
                elif 'sóng thần' in s_lower:
                    provinces_served.update(['Bình Dương', 'Hồ Chí Minh', 'Đồng Nai', 'Bình Phước'])
                elif 'hồ chí minh' in s_lower:
                    provinces_served.update(['Hồ Chí Minh', 'Bình Dương', 'Long An', 'Đồng Nai'])
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

    def process_and_report(self, send_tele=True):
        now = datetime.now()
        now_str = now.strftime('%H:%M %d/%m/%Y')
        curr_time_str = now.strftime('%H:%M')
        window_end = now + timedelta(minutes=90)
        end_time_str = window_end.strftime('%H:%M')

        print(f"[{now_str}] Đang quét đơn tồn Metabase & Lịch xe trong vòng 1h30p ({curr_time_str} ➔ {end_time_str})...")

        try:
            df = self.fetch_live_metabase()
        except Exception as e:
            err_msg = (
                f"⚠️ <b>LỖI KẾT NỐI METABASE (Card {CARD_ID}):</b>\n"
                f"Chi tiết: <code>{str(e)}</code>\n\n"
                f"👉 <i>Vui lòng kiểm tra lại Session Token Metabase.</i>"
            )
            print(err_msg)
            if send_tele:
                self.send_telegram(err_msg)
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

        # Filter transit orders (KhoGiao != KhoHienTai)
        df_transit = df[df['KhoGiao'] != df['KhoHienTai']].copy()
        transit_count = len(df_transit)
        transit_kg = df_transit['KG'].sum()

        # Extract Province for each order
        df_transit['Tinh'] = df_transit['KhoGiao'].apply(extract_province)

        # Get trips departing in the next 1 hour 30 minutes
        upcoming_trips = self.get_upcoming_trips_in_90min(now)
        print(f"Tìm thấy {len(upcoming_trips)} chuyến xe xuất bến trong khung giờ {curr_time_str} - {end_time_str}.")

        route_reports = []
        for tdata in upcoming_trips:
            provinces_served = tdata['ProvincesServed']
            matched_backlog = df_transit[df_transit['Tinh'].isin(provinces_served)].copy()
            if matched_backlog.empty:
                continue

            # Group by Province and KhoGiao
            prov_data = {}
            for prov in sorted(list(provinces_served)):
                p_orders = matched_backlog[matched_backlog['Tinh'] == prov]
                if p_orders.empty:
                    continue

                kg_breakdown = p_orders.groupby('KhoGiao').agg(
                    SoDon=('KhoGiao', 'count'),
                    TongKG=('KG', 'sum')
                ).reset_index().sort_values(by='TongKG', ascending=False)

                prov_data[prov] = {
                    'SoDon': int(p_orders['KhoGiao'].count()),
                    'TongKG': float(p_orders['KG'].sum()),
                    'KhoGiaoList': kg_breakdown.to_dict('records')
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
                    'Provinces': prov_data
                })

        # Sort by departure time HHMM, then highest KG
        route_reports.sort(key=lambda x: (x['HHMM'], -x['TotalKG']))

        # Format Telegram Message as requested
        lines = []
        lines.append("🚨 <b>CẢNH BÁO LỊCH TẢI TUYẾN GẦN NHẤT (1H30P TỚI)</b>")
        lines.append(f"⏰ Thời điểm quét: <b>{now_str}</b> (Quét định kỳ 1h/lần)")
        lines.append(f"⏳ Khung giờ xuất bến: <b>{curr_time_str} ➔ {end_time_str}</b>")
        lines.append(f"📦 Tổng tồn Đài Tư: <b>{total_orders:,} đơn</b> · <b>{total_kg:,.1f} kg</b>")
        lines.append(f"🚚 Hàng cần đi các tỉnh: <b>{transit_count:,} đơn</b> · <b>{transit_kg:,.1f} kg</b>\n")

        if not route_reports:
            lines.append("ℹ️ <i>Trong 1h30p tới không có chuyến xe nào xuất bến khớp với các tỉnh có hàng tồn.</i>")
        else:
            lines.append(f"🚛 <b>DANH SÁCH LỊCH TẢI TUYẾN ({len(route_reports)} TUYẾN KHỚP LỊCH):</b>\n")
            for idx, r in enumerate(route_reports[:6], 1):
                tt_str = f"{r['TrongTai']} kg" if r['TrongTai'] else "Xe cố định"
                lines.append(
                    f"🚛 <b>{idx}. Tuyến <code>{r['MaTuyen']}</code> — Cung giờ: <b>{r['HHMM']}</b></b> (Tải xe: {tt_str})\n"
                    f"   📊 <b>Tổng hàng lên xe: {r['TotalOrders']} đơn · ⚖️ {r['TotalKG']:,.1f} kg</b>"
                )
                for prov_name, pdata in r['Provinces'].items():
                    lines.append(f"   • <b>Tỉnh {prov_name}:</b> {pdata['SoDon']} đơn - {pdata['TongKG']:,.1f} kg")
                    for kg_row in pdata['KhoGiaoList'][:3]:
                        lines.append(f"     - {kg_row['KhoGiao']}: {kg_row['SoDon']} đơn - {kg_row['TongKG']:,.1f} kg")
                    if len(pdata['KhoGiaoList']) > 3:
                        rem_cnt = sum(k['SoDon'] for k in pdata['KhoGiaoList'][3:])
                        rem_kg = sum(k['TongKG'] for k in pdata['KhoGiaoList'][3:])
                        lines.append(f"     <i>... và {len(pdata['KhoGiaoList']) - 3} kho khác ({rem_cnt} đơn - {rem_kg:,.1f} kg)</i>")
                lines.append("")

            if len(route_reports) > 6:
                rem_routes = len(route_reports) - 6
                lines.append(f"<i>... và còn {rem_routes} tuyến xe khác xuất bến trong 1h30p tới.</i>\n")

        lines.append("👉 <i>Vui lòng ưu tiên gom và xếp hàng lên các chuyến xe có giờ xuất bến sớm nhất!</i>")
        msg = "\n".join(lines)

        print("\n" + "=" * 70)
        print(msg)
        print("=" * 70 + "\n")

        if send_tele:
            self.send_telegram(msg)

        return msg

    def send_telegram(self, text):
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("Telegram Token/Chat ID chưa được cấu hình. Bỏ qua gửi tin.")
            return

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

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
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": chunk, "parse_mode": "HTML"}
            try:
                r = requests.post(url, json=payload, timeout=15)
                r.raise_for_status()
                print(f"✅ Đã gửi phần {idx}/{len(chunks)} lên Telegram Channel thành công!")
            except Exception as e:
                print(f"❌ Lỗi gửi Telegram phần {idx}: {e}")

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
    is_daemon = '--daemon' in sys.argv
    advisor = B2BTonAdvisor()
    if is_daemon:
        advisor.run_daemon(interval_seconds=3600)
    else:
        advisor.process_and_report(send_tele=True)
