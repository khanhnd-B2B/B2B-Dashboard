import pandas as pd
import requests
import os
from datetime import datetime, timedelta

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print('Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in environment.')
        import sys
        sys.stdout.reconfigure(encoding='utf-8')
        print('Message preview:')
        print(text)
        return
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'HTML'}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print('Telegram message sent successfully!')
    except Exception as e:
        print(f'Error sending Telegram message: {e}')

def main():
    master_file = 'Data B2B Master.xlsx'
    if not os.path.exists(master_file):
        print(f'Error: {master_file} not found.')
        return
        
    try:
        df = pd.read_excel(master_file)
    except Exception as e:
        print(f'Error reading {master_file}: {e}')
        return

    # Clean dates
    dt_columns = ['ThoiGianNhap', 'InsideThoiGianGanNhat', 'NgayNhap', 'ThoiGianXuatKien']
    for col in dt_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.tz_localize(None)

    if 'KhoiLuongKG' in df.columns:
        df['KhoiLuongKG'] = pd.to_numeric(df['KhoiLuongKG'], errors='coerce').fillna(0)
    else:
        df['KhoiLuongKG'] = 0

    yesterday = (datetime.now() - timedelta(days=1)).date()
    yesterday_str = yesterday.strftime('%d/%m/%Y')

    # 1. San luong ngay hom qua
    df_yest = df[df['NgayNhap'].dt.date == yesterday]
    tong_nhap = len(df_yest)
    tong_kg = df_yest['KhoiLuongKG'].sum()
    
    # Tu lay vs Nhap tu kho khac
    tu_lay_count, tu_lay_kg = 0, 0
    nhap_ve_count, nhap_ve_kg = 0, 0
    if 'NguonNhap' in df_yest.columns:
        df_tu = df_yest[df_yest['NguonNhap'].fillna('').str.contains('Tự', case=False)]
        tu_lay_count = len(df_tu)
        tu_lay_kg = df_tu['KhoiLuongKG'].sum()
        
        df_nhap = df_yest[df_yest['NguonNhap'].fillna('').str.contains('Nhập', case=False)]
        nhap_ve_count = len(df_nhap)
        nhap_ve_kg = df_nhap['KhoiLuongKG'].sum()
    
    # Kho Nhap: Dai Tu vs Hung Yen
    dt_count, dt_kg = 0, 0
    hy_count, hy_kg = 0, 0
    if 'KhoNhap' in df_yest.columns:
        df_dt = df_yest[df_yest['KhoNhap'].fillna('').str.contains('Đài Tư', case=False)]
        dt_count = len(df_dt)
        dt_kg = df_dt['KhoiLuongKG'].sum()
        
        df_hy = df_yest[df_yest['KhoNhap'].fillna('').str.contains('Hưng Yên', case=False)]
        hy_count = len(df_hy)
        hy_kg = df_hy['KhoiLuongKG'].sum()

    # TOP 3 tinh kg
    top_tinh_str = 'N/A'
    if 'TinhGiao' in df_yest.columns:
        top_tinh = df_yest.groupby('TinhGiao')['KhoiLuongKG'].sum().nlargest(3)
        if not top_tinh.empty:
            top_tinh_str = ', '.join([f'{t} ({v:,.0f} kg)' for t, v in top_tinh.items()])

    # 2. Ontime xuat hang (NgayNhap == yesterday)
    df_ot = df_yest.copy()
    if 'KhoLay_ID' in df_ot.columns and 'KhoGiao_ID' in df_ot.columns:
        df_ot = df_ot[df_ot['KhoLay_ID'] != df_ot['KhoGiao_ID']]
    if 'KhoGiao_ID' in df_ot.columns and 'KhoHienTai_ID' in df_ot.columns and 'KhoHienTai' in df_ot.columns:
        cond_exclude = (df_ot['KhoGiao_ID'] == df_ot['KhoHienTai_ID']) & (df_ot['KhoHienTai'].str.contains('Đài Tư|Hưng Yên', case=False, na=False))
        df_ot = df_ot[~cond_exclude]

    tong_don_ontime = len(df_ot)
    ontime_count = 0
    tyle_ontime = 0
    dt_rate, dt_on, dt_tot, dt_tre = 0, 0, 0, 0
    hy_rate, hy_on, hy_tot, hy_tre = 0, 0, 0, 0

    if tong_don_ontime > 0 and 'ThoiGianNhap' in df_ot.columns and 'KhoNhap_ID' in df_ot.columns and 'KhoHienTai_ID' in df_ot.columns:
        df_ot['DeadlineXuat'] = df_ot['ThoiGianNhap'] + pd.Timedelta(hours=24)
        if 'ThoiGianXuatKien' in df_ot.columns:
            df_ot['ThoiGianXuat'] = pd.to_datetime(df_ot['ThoiGianXuatKien'])
            df_ot['DaXuat'] = df_ot['ThoiGianXuat'].notna()
        else:
            is_exported = (df_ot['KhoHienTai_ID'] != df_ot['KhoNhap_ID']) | (df_ot.get('TrangThaiViTriInside', '') == 'Đã xuất khỏi kho thao tác gần nhất')
            df_ot['DaXuat'] = is_exported
            df_ot['ThoiGianXuat'] = pd.to_datetime(df_ot.get('InsideThoiGianGanNhat', pd.NaT))
            
        now = pd.Timestamp.now()
        df_ot['Ontime'] = (df_ot['DaXuat'] & (df_ot['ThoiGianXuat'] <= df_ot['DeadlineXuat'])) | (~df_ot['DaXuat'] & (now <= df_ot['DeadlineXuat']))
        ontime_count = int(df_ot['Ontime'].sum())
        tyle_ontime = (ontime_count / tong_don_ontime * 100) if tong_don_ontime > 0 else 0

        # Đài Tư Ontime
        df_ot_dt = df_ot[df_ot['KhoNhap'].fillna('').str.contains('Đài Tư', case=False)] if 'KhoNhap' in df_ot.columns else pd.DataFrame()
        dt_tot = len(df_ot_dt)
        dt_on = int(df_ot_dt['Ontime'].sum()) if dt_tot > 0 else 0
        dt_rate = (dt_on / dt_tot * 100) if dt_tot > 0 else 0
        dt_tre = dt_tot - dt_on

        # Hưng Yên Ontime
        df_ot_hy = df_ot[df_ot['KhoNhap'].fillna('').str.contains('Hưng Yên', case=False)] if 'KhoNhap' in df_ot.columns else pd.DataFrame()
        hy_tot = len(df_ot_hy)
        hy_on = int(df_ot_hy['Ontime'].sum()) if hy_tot > 0 else 0
        hy_rate = (hy_on / hy_tot * 100) if hy_tot > 0 else 0
        hy_tre = hy_tot - hy_on

    # Build message
    msg = f'<b>📊 BÁO CÁO TỔNG QUAN B2B NGÀY {yesterday_str}</b>\n\n'
    msg += f'<b>1. Sản lượng nhập kho:</b>\n'
    msg += f'- Tổng đơn nhập: <b>{tong_nhap:,}</b> đơn ({tong_kg:,.0f} kg)\n'
    msg += f'  • Kho Đài Tư: <b>{dt_count:,}</b> đơn ({dt_kg:,.0f} kg)\n'
    msg += f'  • Kho Hưng Yên: <b>{hy_count:,}</b> đơn ({hy_kg:,.0f} kg)\n'
    msg += f'  • Tự lấy: <b>{tu_lay_count:,}</b> đơn ({tu_lay_kg:,.0f} kg) | Nhập về: <b>{nhap_ve_count:,}</b> đơn ({nhap_ve_kg:,.0f} kg)\n'
    msg += f'- TOP 3 tỉnh (KG): {top_tinh_str}\n\n'

    msg += f'<b>2. Ontime xuất hàng:</b>\n'
    if tong_don_ontime > 0:
        msg += f'- <b>Tổng thể:</b> <b>{tyle_ontime:.1f}%</b> ({ontime_count:,}/{tong_don_ontime:,} đơn'
        tre_count = tong_don_ontime - ontime_count
        if tre_count > 0:
            msg += f' - {tre_count:,} trễ ⚠️)\n'
        else:
            msg += f' - 0 trễ ✅)\n'

        if dt_tot > 0:
            msg += f'  • <b>Đài Tư:</b> <b>{dt_rate:.1f}%</b> ({dt_on:,}/{dt_tot:,} đơn'
            if dt_tre > 0:
                msg += f' - {dt_tre:,} trễ ⚠️)\n'
            else:
                msg += f' - 0 trễ ✅)\n'

        if hy_tot > 0:
            msg += f'  • <b>Hưng Yên:</b> <b>{hy_rate:.1f}%</b> ({hy_on:,}/{hy_tot:,} đơn'
            if hy_tre > 0:
                msg += f' - {hy_tre:,} trễ ⚠️)\n'
            else:
                msg += f' - 0 trễ ✅)\n'
    else:
        msg += f'- Không có đơn phát sinh cần tính Ontime.\n'

    msg += f'\n👉 Xem chi tiết Dashboard: https://b2b-dashboard-hydt.streamlit.app'

    send_telegram_message(msg)

if __name__ == '__main__':
    main()
