import pandas as pd
import requests
import os
from datetime import datetime, timedelta

# Lấy Token và Chat ID từ GitHub Secrets (hoặc biến môi trường)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Lỗi: Không tìm thấy TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID. Hãy cài đặt trong GitHub Secrets.")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Gửi tin nhắn Telegram thành công!")
    except Exception as e:
        print(f"Lỗi gửi tin nhắn Telegram: {e}")

def main():
    try:
        df = pd.read_csv('master_data.csv')
    except Exception as e:
        print(f"Lỗi đọc data: {e}")
        return
        
    dt_columns = ['ThoiGianTao', 'ThoiGianLayThanhCong', 'ThoiGianXuatKienDauTien']
    for col in dt_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.tz_localize(None)
            
    # Lấy ngày hôm qua (vì báo cáo 8h sáng thường nói về số liệu chốt ngày hôm trước)
    yesterday = (datetime.now() - timedelta(days=1)).date()
    yesterday_str = yesterday.strftime("%d/%m/%Y")
    
    # 1. Báo cáo Sản lượng
    df_tao_yest = df[df['ThoiGianTao'].dt.date == yesterday]
    df_lay_yest = df[df['ThoiGianLayThanhCong'].dt.date == yesterday]
    
    tong_tao = len(df_tao_yest)
    tong_lay = len(df_lay_yest)
    
    # Đơn tồn chưa lấy (tạo hôm qua nhưng chưa có ThoiGianLayThanhCong)
    ton_chua_lay = df_tao_yest['ThoiGianLayThanhCong'].isna().sum()
    
    # 2. Báo cáo Ontime
    df_ontime = df.dropna(subset=['ThoiGianLayThanhCong']).copy()
    df_ontime = df_ontime[df_ontime['ThoiGianLayThanhCong'].dt.date == yesterday]
    df_ontime['GioLay'] = df_ontime['ThoiGianLayThanhCong'].dt.hour
    
    # Quy định Ontime: Các đơn lấy thành công trước 20h
    df_ontime = df_ontime[df_ontime['GioLay'] < 20]
    df_ontime['DeadlineXuat'] = pd.to_datetime(df_ontime['ThoiGianLayThanhCong'].dt.date) + pd.Timedelta(days=1, hours=6)
    
    def check_ontime(row):
        if pd.isna(row['ThoiGianXuatKienDauTien']): return False
        return row['ThoiGianXuatKienDauTien'] <= row['DeadlineXuat']
        
    if not df_ontime.empty:
        df_ontime['Is_Ontime'] = df_ontime.apply(check_ontime, axis=1)
    else:
        df_ontime['Is_Ontime'] = pd.Series(dtype=bool)
        
    tong_don_tinh_ontime = len(df_ontime)
    don_ontime = df_ontime['Is_Ontime'].sum() if not df_ontime.empty else 0
    tyle_ontime = (don_ontime / tong_don_tinh_ontime * 100) if tong_don_tinh_ontime > 0 else 0
    
    # Xây dựng nội dung tin nhắn Telegram bằng HTML
    msg = f"📊 <b>BÁO CÁO TỔNG QUAN B2B NGÀY {yesterday_str}</b>\n\n"
    
    msg += f"📦 <b>1. Sản lượng:</b>\n"
    msg += f"▪️ Tổng đơn tạo: <b>{tong_tao:,}</b> đơn\n"
    msg += f"▪️ Lấy thành công: <b>{tong_lay:,}</b> đơn\n"
    if ton_chua_lay > 0:
        msg += f"⚠️ Còn <b>{ton_chua_lay:,}</b> đơn tạo hôm qua nhưng chưa lấy thành công!\n"
    else:
        msg += f"✅ Đã lấy 100% đơn tạo ngày hôm qua.\n"
        
    msg += f"\n⏱ <b>2. Chất lượng Ontime (Xuất kho trước 6h):</b>\n"
    if tong_don_tinh_ontime > 0:
        msg += f"▪️ Tỷ lệ Ontime đạt: <b>{tyle_ontime:.1f}%</b> ({don_ontime}/{tong_don_tinh_ontime} đơn)\n"
        if tyle_ontime < 100:
            msg += f"⚠️ Cảnh báo: Có <b>{tong_don_tinh_ontime - don_ontime}</b> đơn bị trễ (Late) không xuất đúng hạn.\n"
    else:
        msg += f"▪️ Không có đơn nào lấy trước 20h để tính Ontime.\n"
        
    msg += f"\n🌐 <i>Xem biểu đồ chi tiết từng KH tại: <a href='https://b2b-dashboard-dsgkivhypxmlqtjujsic2d.streamlit.app'>Dashboard</a></i>"
    
    # Gửi tin nhắn
    send_telegram_message(msg)

if __name__ == "__main__":
    main()
