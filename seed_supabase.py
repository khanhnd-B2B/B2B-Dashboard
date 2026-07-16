"""
Script đổ dữ liệu ban đầu lên Supabase Cloud Database.
Chạy 1 lần duy nhất sau khi đã cấu hình DATABASE_URL.

Cách chạy:
  python seed_supabase.py "postgresql://postgres.[ref]:[PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
"""
import pandas as pd
import sys
import io
import requests
import re
import os
from datetime import datetime, time
from sqlalchemy import create_engine, text

sys.stdout.reconfigure(encoding='utf-8')

if len(sys.argv) < 2:
    print("Cách dùng: python seed_supabase.py <DATABASE_URL>")
    print('Ví dụ: python seed_supabase.py "postgresql://postgres.xxx:password@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"')
    sys.exit(1)

DATABASE_URL = sys.argv[1]
engine = create_engine(DATABASE_URL)

# Create tables
with engine.connect() as conn:
    conn.execute(text('''
        CREATE TABLE IF NOT EXISTS provinces_mapping (
            id SERIAL PRIMARY KEY,
            province TEXT UNIQUE,
            level1_code TEXT,
            level2_code TEXT,
            fixed_route TEXT
        )
    '''))
    conn.execute(text('''
        CREATE TABLE IF NOT EXISTS routes_schedule (
            id SERIAL PRIMARY KEY,
            route_code TEXT,
            hub TEXT,
            departure_time TEXT
        )
    '''))
    # Clear existing data
    conn.execute(text("DELETE FROM provinces_mapping"))
    conn.execute(text("DELETE FROM routes_schedule"))
    conn.commit()

print("Tables created and cleared.")

# 1. PROVINCE MAPPING
sqllab_path = r'd:\LophocAI\quanlyB2B\sqllab_untitled_query_49_20260712T190431.xlsx'
df_sql = pd.read_excel(sqllab_path)
province_mapping = {}

for _, row in df_sql.dropna(subset=['sort_code', 'TinhGiao']).iterrows():
    tinh = str(row['TinhGiao']).strip()
    sc = str(row['sort_code']).upper()
    parts = sc.split('-')
    ma_bac_1 = ''
    ma_bac_2 = ''
    for i, p in enumerate(parts):
        p = p.strip()
        if p.isalpha():
            ma_bac_1 = p
            if i > 0 and parts[i-1].strip().isdigit():
                ma_bac_2 = parts[i-1].strip()
            break
    if not ma_bac_1: continue
    if tinh not in province_mapping:
        province_mapping[tinh] = {}
    combo = (ma_bac_1, ma_bac_2)
    province_mapping[tinh][combo] = province_mapping[tinh].get(combo, 0) + row['SoLuongDon']

final_provinces = []
for tinh, combos in province_mapping.items():
    best_combo = max(combos.items(), key=lambda x: x[1])[0]
    final_provinces.append({
        'province': tinh,
        'level1_code': best_combo[0],
        'level2_code': best_combo[1]
    })
df_prov = pd.DataFrame(final_provinces).sort_values('province')

# 2. ROUTES & SCHEDULES
url2 = 'https://docs.google.com/spreadsheets/d/1_rqhL3OKNv5lYid3FkGtbWly7rXzfUVRbX_m1OrrEtc/export?format=xlsx'
res2 = requests.get(url2)
xl2 = pd.ExcelFile(io.BytesIO(res2.content))
routes_data = []

def parse_time(t_val):
    if pd.isna(t_val): return None
    if isinstance(t_val, time): return t_val
    if isinstance(t_val, datetime): return t_val.time()
    t_str = str(t_val).strip()
    m = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', t_str)
    if m:
        h, min_val, s = m.groups()
        return time(int(h), int(min_val), int(s) if s else 0)
    return None

df_6t = pd.read_excel(xl2, sheet_name='6 TỈNH ')
for _, row in df_6t.iterrows():
    route = str(row.get('Mã chuyến')).strip()
    loc = str(row.get('Tên địa điểm')).lower()
    t_depart = parse_time(row.get('Giờ đi'))
    if route == 'nan' or t_depart is None: continue
    hub = None
    if 'hưng yên' in loc or 'hy' in loc: hub = 'HY'
    elif 'đài tư' in loc or 'dương xá' in loc or 'hn' in loc: hub = 'HN'
    if hub: routes_data.append({'route_code': route, 'hub': hub, 'departure_time': t_depart.strftime('%H:%M:%S')})

df_lv = pd.read_excel(xl2, sheet_name='LIÊN VÙNG')
for _, row in df_lv.iterrows():
    route = str(row.get('Tên tuyến')).strip()
    loc = str(row.get('Tên Kho (tóm tắt)')).lower()
    t_depart = parse_time(row.get('Giờ rời'))
    if route == 'nan' or t_depart is None: continue
    hub = None
    if loc.startswith('hưng yên') or 'hy_' in route.lower(): hub = 'HY'
    if loc.startswith('hà nội') or 'hn_' in route.lower() or 'đài tư' in loc: hub = 'HN'
    if hub: routes_data.append({'route_code': route, 'hub': hub, 'departure_time': t_depart.strftime('%H:%M:%S')})

df_mb = pd.read_excel(xl2, sheet_name='MIỀN BẮC')
df_mb['Tên tuyến'] = df_mb['Tên tuyến'].ffill()
for _, row in df_mb.iterrows():
    route = str(row.get('Tên tuyến')).strip()
    loc = str(row.get('Tên bưu cục')).lower()
    t_depart = parse_time(row.get('Giờ rời'))
    if route == 'nan' or t_depart is None: continue
    hub = None
    if 'hưng yên' in loc or 'hy' in loc: hub = 'HY'
    elif 'đài tư' in loc or 'dương xá' in loc or 'hn' in loc: hub = 'HN'
    if hub: routes_data.append({'route_code': route, 'hub': hub, 'departure_time': t_depart.strftime('%H:%M:%S')})

df_routes = pd.DataFrame(routes_data).drop_duplicates(subset=['route_code', 'hub', 'departure_time'])

# Map routes to provinces
def find_matching_routes(tinh):
    tinh_simp = tinh.lower().replace(' ', '').replace('đ', 'd').replace('ư', 'u').replace('ơ', 'o').replace('ô', 'o')
    matched = []
    for r in df_routes['route_code'].unique():
        r_lower = r.lower().replace('đ', 'd')
        if tinh_simp in r_lower or (len(tinh.split()) > 1 and "".join([w[0] for w in tinh.lower().split()]) in r_lower):
             matched.append(r)
    return ", ".join(list(set(matched)))

df_prov['fixed_route'] = df_prov['province'].apply(find_matching_routes)

# Insert into Cloud DB
df_prov.to_sql('provinces_mapping', engine, if_exists='append', index=False)
print(f"Inserted {len(df_prov)} provinces.")

df_routes.to_sql('routes_schedule', engine, if_exists='append', index=False)
print(f"Inserted {len(df_routes)} routes.")

print("\n✅ Seed completed successfully! Data is now on Supabase Cloud.")
