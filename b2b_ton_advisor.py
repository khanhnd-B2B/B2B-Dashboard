import requests
import json
import pandas as pd
import os
import sys
import time
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# Configuration
METABASE_URL = os.environ.get('METABASE_URL', 'https://data-bi.ghn.vn')
METABASE_SESSION = os.environ.get('METABASE_SESSION', '911df869-0b66-4af3-a701-a10a563c33ad')
CARD_ID = int(os.environ.get('METABASE_CARD_ID', 6287))

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8370307476:AAEsPB2UZ0zQHMTEWPGFFBw7fUYuWsePxPM')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '-1004492922071')

TRIPS_FILE = os.path.join(os.path.dirname(__file__), 'data chuyến cố định 7 ngày gần nhất 3.9.xlsx')

# Destination routing map from HN02 (Đài Tư)
# Maps region/province to target hub and route prefix preference
REGION_ROUTING = {
    # Hưng Yên Hub & provinces routed via Hưng Yên
    'hưng yên': {'hub': 'Kho Trung Chuyển Hưng Yên 01', 'shuttle_prefix': 'HN_HY_', 'desc': 'HN02 ➔ TC Hưng Yên'},
    'ân thi': {'hub': 'Kho Trung Chuyển Hưng Yên 01', 'shuttle_prefix': 'HN_HY_', 'desc': 'HN02 ➔ TC Hưng Yên ➔ Ân Thi'},
    'phố hiến': {'hub': 'Kho Trung Chuyển Hưng Yên 01', 'shuttle_prefix': 'HN_HY_', 'desc': 'HN02 ➔ TC Hưng Yên ➔ Phố Hiến'},
    'mỹ lộc': {'hub': 'Kho Trung Chuyển Hưng Yên 01', 'shuttle_prefix': 'HN_HY_', 'desc': 'HN02 ➔ TC Hưng Yên ➔ Nam Định'},
    'nam định': {'hub': 'Kho Trung Chuyển Hưng Yên 01', 'shuttle_prefix': 'HN_HY_', 'desc': 'HN02 ➔ TC Hưng Yên ➔ Nam Định'},
    'ninh bình': {'hub': 'Kho Trung Chuyển Hưng Yên 01', 'shuttle_prefix': 'HN_HY_', 'desc': 'HN02 ➔ TC Hưng Yên ➔ Ninh Bình'},
    'yên khánh': {'hub': 'Kho Trung Chuyển Hưng Yên 01', 'shuttle_prefix': 'HN_HY_', 'desc': 'HN02 ➔ TC Hưng Yên ➔ Ninh Bình'},
    'hải dương': {'hub': 'Kho Trung Chuyển Hưng Yên 01', 'shuttle_prefix': 'HN_HY_', 'desc': 'HN02 ➔ TC Hưng Yên ➔ Hải Dương'},
    'thái bình': {'hub': 'Kho Trung Chuyển Hưng Yên 01', 'shuttle_prefix': 'HN_HY_', 'desc': 'HN02 ➔ TC Hưng Yên ➔ Thái Bình'},
    'hà nam': {'hub': 'Kho Trung Chuyển Hưng Yên 01', 'shuttle_prefix': 'HN_HY_', 'desc': 'HN02 ➔ TC Hưng Yên ➔ Hà Nam'},
    
    # Direct provincial KCTs from HN02
    'thanh hoá': {'hub': 'Kho Chuyển Tiếp Thanh Hóa', 'shuttle_prefix': 'HN_TH_', 'desc': 'Tuyến đi Thanh Hóa'},
    'thanh hóa': {'hub': 'Kho Chuyển Tiếp Thanh Hóa', 'shuttle_prefix': 'HN_TH_', 'desc': 'Tuyến đi Thanh Hóa'},
    'nghệ an': {'hub': 'Kho Trung Chuyển Nghệ An', 'shuttle_prefix': 'HN_NA_', 'desc': 'Tuyến đi Nghệ An'},
    'vinh': {'hub': 'Kho Trung Chuyển Nghệ An', 'shuttle_prefix': 'HN_NA_', 'desc': 'Tuyến đi Nghệ An'},
    'hải phòng': {'hub': 'Kho Chuyển Tiếp Hải Phòng', 'shuttle_prefix': 'HN_HaiPhong_', 'desc': 'Tuyến đi Hải Phòng'},
    'quảng ninh': {'hub': 'Kho Chuyển Tiếp Quảng Ninh', 'shuttle_prefix': 'HN_QuangNinh_', 'desc': 'Tuyến đi Quảng Ninh'},
    'thái nguyên': {'hub': 'Kho Chuyển Tiếp Thái Nguyên', 'shuttle_prefix': 'HN_ThaiNguyen_', 'desc': 'Tuyến đi Thái Nguyên'},
    'lạng sơn': {'hub': 'Kho Chuyển Tiếp Lạng Sơn', 'shuttle_prefix': 'HN_LangSon_', 'desc': 'Tuyến đi Lạng Sơn'},
    'phú thọ': {'hub': 'Kho Chuyển Tiếp Phú Thọ', 'shuttle_prefix': 'HN_PhuTho_', 'desc': 'Tuyến đi Phú Thọ'},
    'vĩnh phúc': {'hub': 'Kho Chuyển Tiếp Vĩnh Phúc', 'shuttle_prefix': 'HN_VinhPhuc_', 'desc': 'Tuyến đi Vĩnh Phúc'},
    'bắc giang': {'hub': 'Kho Chuyển Tiếp Bắc Giang', 'shuttle_prefix': 'BacGiang_', 'desc': 'Tuyến đi Bắc Giang'},
    'yên bái': {'hub': 'Kho Chuyển Tiếp Yên Bái', 'shuttle_prefix': 'YenBai_', 'desc': 'Tuyến đi Yên Bái'},
    'sơn la': {'hub': 'Kho Chuyển Tiếp Sơn La', 'shuttle_prefix': 'HN_SonLa_', 'desc': 'Tuyến đi Sơn La'},
    'hòa bình': {'hub': 'Kho Chuyển Tiếp Hoà Bình', 'shuttle_prefix': 'HoaBinh_', 'desc': 'Tuyến đi Hoà Bình'},
    'hoà bình': {'hub': 'Kho Chuyển Tiếp Hoà Bình', 'shuttle_prefix': 'HoaBinh_', 'desc': 'Tuyến đi Hoà Bình'},
    'lào cai': {'hub': 'Kho Chuyển Tiếp Lào Cai', 'shuttle_prefix': 'HN_LaoCai_', 'desc': 'Tuyến đi Lào Cai'},
    'tuyên quang': {'hub': 'Kho Chuyển Tiếp Tuyên Quang', 'shuttle_prefix': 'TuyenQuang_', 'desc': 'Tuyến đi Tuyên Quang'},
    
    # Miền Trung & Miền Nam
    'đà nẵng': {'hub': 'Kho Trung Chuyển Đà Nẵng', 'shuttle_prefix': 'HN_ĐN_', 'desc': 'Tuyến đi Đà Nẵng'},
    'hồ chí minh': {'hub': 'Kho Trung Chuyển Hồ Chí Minh 01', 'shuttle_prefix': 'HN_HCM', 'desc': 'Tuyến đi Hồ Chí Minh'},
    'hcm': {'hub': 'Kho Trung Chuyển Hồ Chí Minh 01', 'shuttle_prefix': 'HN_HCM', 'desc': 'Tuyến đi Hồ Chí Minh'},
    'thủ đức': {'hub': 'Kho Trung Chuyển Hồ Chí Minh 01', 'shuttle_prefix': 'HN_HCM', 'desc': 'Tuyến đi TP Thủ Đức (HCM)'},
    'bình dương': {'hub': 'Kho Chuyển Tiếp Sóng Thần-Bình Dương', 'shuttle_prefix': 'HN_HCM', 'desc': 'Tuyến đi Sóng Thần - Bình Dương'},
    'sóng thần': {'hub': 'Kho Chuyển Tiếp Sóng Thần-Bình Dương', 'shuttle_prefix': 'HN_HCM', 'desc': 'Tuyến đi Sóng Thần - Bình Dương'},
    'dĩ an': {'hub': 'Kho Chuyển Tiếp Sóng Thần-Bình Dương', 'shuttle_prefix': 'HN_HCM', 'desc': 'Tuyến đi Sóng Thần - Bình Dương'},
    'đồng nai': {'hub': 'Kho Chuyển Tiếp Đồng Nai', 'shuttle_prefix': 'HN_ĐNAI_', 'desc': 'Tuyến đi Đồng Nai'},
    'long an': {'hub': 'Kho Trung Chuyển Hồ Chí Minh 01', 'shuttle_prefix': 'HN_HCM', 'desc': 'Tuyến đi Long An (qua HCM)'},
    'đức hòa': {'hub': 'Kho Trung Chuyển Hồ Chí Minh 01', 'shuttle_prefix': 'HN_HCM', 'desc': 'Tuyến đi Đức Hòa (qua HCM)'},
    
    # Bắc Ninh & Nội thành Hà Nội (Dương Xá / Đài Tư)
    'bắc ninh': {'hub': 'Kho Trung Chuyển Dương Xá', 'shuttle_prefix': 'LB_LAYHN_', 'desc': 'Tuyến Bắc Ninh / Dương Xá'},
    'tiên du': {'hub': 'Kho Trung Chuyển Dương Xá', 'shuttle_prefix': 'LB_LAYHN_', 'desc': 'Tuyến Bắc Ninh / Dương Xá'},
    'dương xá': {'hub': 'Kho Trung Chuyển Dương Xá', 'shuttle_prefix': 'HN_HY_DX_', 'desc': 'Tuyến Dương Xá'},
}

class B2BTonAdvisor:
    def __init__(self, session_token=METABASE_SESSION):
        self.session_token = session_token
        self._load_trips()

    def _load_trips(self):
        if not os.path.exists(TRIPS_FILE):
            print(f"Warning: Không tìm thấy file {TRIPS_FILE}")
            self.routes = {}
            return

        df_trips = pd.read_excel(TRIPS_FILE, header=1)
        df_trips['GioDuKienBatDau_GMT7'] = pd.to_datetime(df_trips['GioDuKienBatDau_GMT7'], errors='coerce')
        df_trips['Time_HHMM'] = df_trips['GioDuKienBatDau_GMT7'].dt.strftime('%H:%M')

        # Routes departing from Đài Tư (LDTSC)
        df_ldtsc = df_trips[df_trips['MaKho'] == 'LDTSC'].copy()
        self.routes = {}
        for _, row in df_ldtsc.iterrows():
            mt = str(row['MaTuyen']).strip()
            stops_str = str(row['ToanBoDiemDi']).strip()
            stops = [s.strip() for s in stops_str.split('→')]
            hhmm = row['Time_HHMM']
            trongtai = row.get('TrongTai', 0)

            if mt not in self.routes:
                self.routes[mt] = {
                    'MaTuyen': mt,
                    'ToanBoDiemDi': stops_str,
                    'Stops': stops,
                    'StopsLower': [s.lower() for s in stops],
                    'Hours': set(),
                    'TrongTai': trongtai
                }
            if pd.notna(hhmm):
                self.routes[mt]['Hours'].add(hhmm)

    def fetch_live_data(self):
        url = f'{METABASE_URL}/api/card/{CARD_ID}/query/json'
        headers = {
            'X-Metabase-Session': self.session_token,
            'Cookie': f'metabase.SESSION={self.session_token}',
            'Content-Type': 'application/json'
        }
        res = requests.post(url, headers=headers, json={}, timeout=40)
        res.raise_for_status()
        return pd.DataFrame(res.json())

    def match_route(self, kho_giao, current_time):
        kg_clean = kho_giao.strip().lower()
        curr_hhmm = current_time.strftime('%H:%M')

        matched = []
        routing_info = None

        # 1. Check if matches REGION_ROUTING dictionary
        for kw, r_info in REGION_ROUTING.items():
            if kw in kg_clean:
                routing_info = r_info
                target_hub = r_info['hub'].lower()
                shuttle_pfx = r_info['shuttle_prefix']
                
                # First check for direct shuttles matching prefix
                for mt, rdata in self.routes.items():
                    if mt.startswith(shuttle_pfx) or shuttle_pfx in mt:
                        # Ensure target hub is an early stop (stop 1 or 2)
                        for idx, s in enumerate(rdata['StopsLower']):
                            if target_hub in s and idx <= 2:
                                matched.append((mt, rdata, rdata['Stops'][idx], r_info['desc'], idx, True))
                                break
                                
                # If no prefix match, check routes that stop at target hub early
                if not matched:
                    for mt, rdata in self.routes.items():
                        for idx, s in enumerate(rdata['StopsLower']):
                            if target_hub in s and idx <= 2:
                                matched.append((mt, rdata, rdata['Stops'][idx], r_info['desc'], idx, False))
                                break
                if matched:
                    break

        # 2. Check direct stop match in all routes
        if not matched:
            for mt, rdata in self.routes.items():
                for idx, s in enumerate(rdata['StopsLower']):
                    if kg_clean in s or s in kg_clean:
                        matched.append((mt, rdata, rdata['Stops'][idx], "Tuyến thẳng", idx, True))
                        break

        # 3. Hanoi local
        if not matched and any(k in kg_clean for k in ['(hno)', 'hà nội', 'hn']):
            for mt, rdata in self.routes.items():
                if 'dương xá' in rdata['ToanBoDiemDi'].lower() or 'ckhno' in mt.lower() or 'layhn' in mt.lower():
                    matched.append((mt, rdata, "Nội thành HN / KTC Dương Xá", "Nội thành HN", 1, True))

        if not matched:
            return None

        # Calculate nearest departure time
        results = []
        for mt, rdata, target_stop, r_type, stop_idx, is_prio in matched:
            hours = sorted(list(rdata['Hours']))
            if not hours:
                continue
            next_h = None
            for h in hours:
                if h >= curr_hhmm:
                    next_h = h
                    break
            is_tomorrow = False
            if next_h is None:
                next_h = hours[0]
                is_tomorrow = True

            results.append({
                'MaTuyen': mt,
                'RouteType': r_type,
                'TargetStop': target_stop,
                'NextHour': next_h,
                'IsTomorrow': is_tomorrow,
                'AllHours': hours,
                'StopIdx': stop_idx,
                'IsPrio': is_prio,
                'TrongTai': rdata.get('TrongTai', 0),
                'ToanBoDiemDi': rdata['ToanBoDiemDi']
            })

        # Sort: IsTomorrow (False first), NextHour (earliest), IsPrio (True first), StopIdx (earliest stop)
        results.sort(key=lambda x: (x['IsTomorrow'], x['NextHour'], not x['IsPrio'], x['StopIdx']))
        return results[0] if results else None

    def process_and_report(self, send_tele=True):
        now = datetime.now()
        now_str = now.strftime('%H:%M %d/%m/%Y')
        print(f"[{now_str}] Đang lấy dữ liệu từ Metabase Card {CARD_ID}...")

        try:
            df = self.fetch_live_data()
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

        # Extract KG column (priority: KL_TinhCuoc_Kg -> CanNangThucTe_Kg -> CanNangQuyDoi_Kg)
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

        # Group by KhoGiao
        grouped = df_transit.groupby('KhoGiao').agg(
            SoDon=('KhoGiao', 'count'),
            TongKG=('KG', 'sum')
        ).reset_index()

        summary = []
        for _, row in grouped.iterrows():
            kg = row['KhoGiao']
            cnt = int(row['SoDon'])
            kg_weight = float(row['TongKG'])

            match = self.match_route(kg, now)
            if match:
                tm_str = f"{match['NextHour']} (Hôm nay)" if not match['IsTomorrow'] else f"{match['NextHour']} (Ngày mai)"
                summary.append({
                    'KhoGiao': kg,
                    'SoDon': cnt,
                    'TongKG': kg_weight,
                    'MaTuyen': match['MaTuyen'],
                    'RouteType': match['RouteType'],
                    'GioXuatBen': tm_str,
                    'GioGoc': match['NextHour'],
                    'IsTomorrow': match['IsTomorrow'],
                    'AllHours': ", ".join(match['AllHours']),
                    'TrongTai': match.get('TrongTai', 0)
                })
            else:
                summary.append({
                    'KhoGiao': kg,
                    'SoDon': cnt,
                    'TongKG': kg_weight,
                    'MaTuyen': 'Chưa map được tuyến',
                    'RouteType': '-',
                    'GioXuatBen': '-',
                    'GioGoc': '99:99',
                    'IsTomorrow': True,
                    'AllHours': '-',
                    'TrongTai': 0
                })

        # Sort summary by: Departure time, then highest KG
        summary.sort(key=lambda x: (x['IsTomorrow'], x['GioGoc'], -x['TongKG'], -x['SoDon']))

        # Format Telegram Message
        lines = []
        lines.append("🚨 <b>CẢNH BÁO ĐƠN TỒN B2B & LỊCH XE XUẤT BẾN GẦN NHẤT</b>")
        lines.append(f"⏰ Thời điểm quét: <b>{now_str}</b>")
        lines.append(f"📍 Kho hiện tại: <b>Kho B2B - Đài Tư - Hà Nội</b>")
        lines.append(
            f"📦 Tổng đơn tồn: <b>{total_orders:,} đơn</b> · <b>{total_kg:,.1f} kg</b>\n"
            f"🚚 Cần xuất đi: <b>{transit_count:,} đơn</b> · <b>{transit_kg:,.1f} kg</b> (qua {len(grouped)} kho giao)\n"
        )

        lines.append("🚛 <b>DANH SÁCH TUYẾN XE GẦN NHẤT CẦN XẾP HÀNG:</b>")
        for idx, item in enumerate(summary[:15], 1):
            kg_info = f"{item['TongKG']:,.1f} kg" if item['TongKG'] > 0 else "0 kg"
            lines.append(
                f"<b>{idx}. {item['KhoGiao']}</b>\n"
                f"   📦 Sản lượng: <b>{item['SoDon']}</b> đơn · ⚖️ <b>{kg_info}</b>\n"
                f"   ➔ Tuyến: <code>{item['MaTuyen']}</code> [{item['RouteType']}]\n"
                f"   ➔ ⏰ Có mặt Đài Tư: <b>{item['GioXuatBen']}</b> (Khung giờ: {item['AllHours']})"
            )

        if len(summary) > 15:
            rem_orders = sum(s['SoDon'] for s in summary[15:])
            rem_kg = sum(s['TongKG'] for s in summary[15:])
            lines.append(f"\n<i>... và còn {len(summary) - 15} kho giao khác ({rem_orders} đơn · {rem_kg:,.1f} kg).</i>")

        lines.append(f"\n👉 <i>Tự động quét Metabase 1 tiếng/lần. Vui lòng ưu tiên xếp hàng lên các xe có giờ xuất bến sớm nhất!</i>")
        msg = "\n".join(lines)

        print("\n" + "="*70)
        print(msg)
        print("="*70 + "\n")

        if send_tele:
            self.send_telegram(msg)

        return msg

    def send_telegram(self, text):
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("Telegram Token/Chat ID chưa được cấu hình. Bỏ qua gửi tin.")
            return
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
        try:
            r = requests.post(url, json=payload, timeout=12)
            r.raise_for_status()
            print("✅ Đã gửi cảnh báo lên Telegram Channel thành công!")
        except Exception as e:
            print(f"❌ Lỗi gửi Telegram: {e}")

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
