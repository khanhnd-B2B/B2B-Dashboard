import pandas as pd
import requests
import os
from datetime import datetime, timedelta

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in environment.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Telegram message sent successfully!")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

def main():
    try:
        df = pd.read_csv('master_data.csv')
    except Exception as e:
        print(f"Error reading data: {e}")
        return

    dt_columns = ['ThoiGianTao', 'ThoiGianLayThanhCong', 'ThoiGianXuatKienDauTien']
    for col in dt_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.tz_localize(None)

    weight_col = 'KL_TinhCuoc_kg'
    if weight_col in df.columns:
        df[weight_col] = pd.to_numeric(df[weight_col], errors='coerce').fillna(0)
    else:
        df[weight_col] = 0

    yesterday = (datetime.now() - timedelta(days=1)).date()
    yesterday_str = yesterday.strftime("%d/%m/%Y")

    # 1. San luong
    df_tao_yest = df[df['ThoiGianTao'].dt.date == yesterday]
    df_lay_yest = df[df['ThoiGianLayThanhCong'].dt.date == yesterday]
    tong_tao = len(df_tao_yest)
    tong_lay = len(df_lay_yest)
    ton_chua_lay = df_tao_yest['ThoiGianLayThanhCong'].isna().sum()

    # Don nhay BC
    don_bc = 0
    if 'KhoGiao' in df_tao_yest.columns:
        don_bc = (~df_tao_yest['KhoGiao'].fillna('').str.contains('Kho', case=False)).sum()

    # Top 3 tinh kg
    top_tinh = df_tao_yest.groupby('TinhGiao')[weight_col].sum().nlargest(3)
    top_tinh_str = ", ".join([f"{t} ({v:,.1f} kg)" for t, v in top_tinh.items()]) if not top_tinh.empty else "N/A"

    # 2. Ontime (loai tru Dai Tu)
    df_ontime = df.dropna(subset=['ThoiGianLayThanhCong']).copy()
    if 'KhoGiao' in df_ontime.columns:
        df_ontime = df_ontime[~df_ontime['KhoGiao'].fillna('').str.contains('Dai Tu|Đài Tư', case=False)]
    df_ontime = df_ontime[df_ontime['ThoiGianLayThanhCong'].dt.date == yesterday]
    df_ontime['GioLay'] = df_ontime['ThoiGianLayThanhCong'].dt.hour
    import numpy as np
    base_date = pd.to_datetime(df_ontime['ThoiGianLayThanhCong'].dt.date)
    df_ontime['DeadlineXuat'] = np.where(
        df_ontime['GioLay'] < 20,
        base_date + pd.Timedelta(days=1, hours=6),
        base_date + pd.Timedelta(days=1, hours=20)
    )

    def check_ontime(row):
        if pd.isna(row['ThoiGianXuatKienDauTien']): return False
        return row['ThoiGianXuatKienDauTien'] <= row['DeadlineXuat']

    tong_don_ontime = len(df_ontime)
    don_ontime = 0
    if tong_don_ontime > 0:
        df_ontime['Is_Ontime'] = df_ontime.apply(check_ontime, axis=1)
        don_ontime = df_ontime['Is_Ontime'].sum()
    tyle_ontime = (don_ontime / tong_don_ontime * 100) if tong_don_ontime > 0 else 0

    # Build message
    msg = f"<b>BAO CAO TONG QUAN B2B NGAY {yesterday_str}</b>\n\n"

    msg += f"<b>1. San luong:</b>\n"
    msg += f"- Tong don tao: <b>{tong_tao:,}</b>\n"
    msg += f"- Lay thanh cong: <b>{tong_lay:,}</b>\n"
    if ton_chua_lay > 0:
        msg += f"- Con <b>{ton_chua_lay:,}</b> don chua lay thanh cong!\n"
    if don_bc > 0:
        msg += f"- Don nhay BC: <b>{don_bc:,}</b> don\n"
    msg += f"- TOP 3 tinh kg: {top_tinh_str}\n"

    msg += f"\n<b>2. Ontime xuat hang:</b>\n"
    if tong_don_ontime > 0:
        msg += f"- Ty le Ontime: <b>{tyle_ontime:.1f}%</b> ({don_ontime}/{tong_don_ontime})\n"
        if tyle_ontime < 100:
            msg += f"- Co <b>{tong_don_ontime - don_ontime}</b> don bi tre.\n"
    else:
        msg += f"- Khong co don nao de tinh Ontime.\n"

    msg += f"\nXem chi tiet: https://b2b-dashboard-dsgkivhypxmlqtjujsic2d.streamlit.app"

    send_telegram_message(msg)

if __name__ == "__main__":
    main()
