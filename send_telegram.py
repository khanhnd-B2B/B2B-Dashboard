import pandas as pd
import requests
import os
from datetime import datetime, timedelta

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print('Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in environment.')
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
    
    # Tu lay vs Nhap tu kho khac
    tu_lay_count = 0
    nhap_ve_count = 0
    if 'NguonNhap' in df_yest.columns:
        tu_lay_count = int(df_yest['NguonNhap'].fillna('').str.contains('Tự', case=False).sum())
        nhap_ve_count = int(df_yest['NguonNhap'].fillna('').str.contains('Nhập', case=False).sum())
        
    tong_kg = df_yest['KhoiLuongKG'].sum()
    
    # Kho Nhap: Dai Tu vs Hung Yen
    dt_count = 0
    hy_count = 0
    if 'KhoNhap' in df_yest.columns:
        dt_count = int(df_yest['KhoNhap'].fillna('').str.contains('Đài Tư', case=False).sum())
        hy_count = int(df_yest['KhoNhap'].fillna('').str.contains('Hưng Yên', case=False).sum())

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

    # Build message
    msg = f'<b>📊 BÁO CÁO TỔNG QUAN B2B NGÀY {yesterday_str}</b>\n\n'
    msg += f'<b>1. Sản lượng nhập kho:</b>\n'
    msg += f'- Tổng đơn nhập: <b>{tong_nhap:,}</b> đơn ({tong_kg:,.0f} kg)\n'
    msg += f'  • Tự lấy: <b>{tu_lay_count:,}</b> đơn | Nhập về: <b>{nhap_ve_count:,}</b> đơn\n'
    msg += f'  • Kho Đài Tư: <b>{dt_count:,}</b> đơn | Kho Hưng Yên: <b>{hy_count:,}</b> đơn\n'
    msg += f'- TOP 3 tỉnh (KG): {top_tinh_str}\n\n'

    msg += f'<b>2. Ontime xuất hàng:</b>\n'
    if tong_don_ontime > 0:
        msg += f'- Tỷ lệ Ontime: <b>{tyle_ontime:.1f}%</b> ({ontime_count:,}/{tong_don_ontime:,} đơn)\n'
        tre_count = tong_don_ontime - ontime_count
        if tre_count > 0:
            msg += f'- Số đơn trễ hạn: <b>{tre_count:,}</b> đơn ⚠️\n'
        else:
            msg += f'- Đạt 100% Ontime ✅\n'
    else:
        msg += f'- Không có đơn phát sinh cần tính Ontime.\n'

    msg += f'\n👉 Xem chi tiết Dashboard: https://b2b-dashboard-hydt.streamlit.app'

    send_telegram_message(msg)

if __name__ == '__main__':
    main()
