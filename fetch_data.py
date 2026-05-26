import pandas as pd
import os
from datetime import datetime, timedelta

def main():
    print(f"[{datetime.now()}] Starting to fetch new data from Google Sheets...")
    url = "https://docs.google.com/spreadsheets/d/1YNuLmUv6FRVMieyQy4JVnFscvkqnBdygzaWaQvOWMzU/export?format=csv&gid=0"
    
    try:
        new_df = pd.read_csv(url)
        print(f"Successfully downloaded {len(new_df)} rows from Google Sheets.")
    except Exception as e:
        print(f"Error downloading data: {e}")
        return

    master_file = 'master_data.csv'
    
    if os.path.exists(master_file):
        try:
            master_df = pd.read_csv(master_file)
            print(f"Loaded existing master_data.csv with {len(master_df)} rows.")
            
            # Gộp dữ liệu: Ưu tiên dữ liệu mới nhất (nằm ở new_df)
            combined_df = pd.concat([master_df, new_df], ignore_index=True)
            # Dùng keep='last' để giữ lại trạng thái mới nhất từ new_df
            combined_df = combined_df.drop_duplicates(subset=['order_code'], keep='last')
            print(f"After merge and deduplication: {len(combined_df)} rows.")
            
        except Exception as e:
            print(f"Error reading old master file: {e}. Will create a new one.")
            combined_df = new_df
    else:
        combined_df = new_df

    # Lọc giữ lại dữ liệu 60 ngày gần nhất (2 tháng)
    print("Filtering data for the last 60 days...")
    if 'ThoiGianTao' in combined_df.columns:
        # Tạm tạo cột datetime để so sánh
        combined_df['ThoiGianTao_dt'] = pd.to_datetime(combined_df['ThoiGianTao'], errors='coerce').dt.tz_localize(None)
        limit_date = datetime.now() - timedelta(days=60)
        
        # Chỉ giữ lại các dòng có thời gian tạo >= limit_date hoặc bị rỗng thời gian tạo
        combined_df = combined_df[(combined_df['ThoiGianTao_dt'] >= limit_date) | (combined_df['ThoiGianTao_dt'].isna())]
        
        # Xóa cột tạm
        combined_df = combined_df.drop(columns=['ThoiGianTao_dt'])
        
    # Ghi lại file master
    combined_df.to_csv(master_file, index=False, encoding='utf-8-sig')
    print(f"[{datetime.now()}] Update successful! Total rows in master_data.csv: {len(combined_df)}")

if __name__ == "__main__":
    main()
