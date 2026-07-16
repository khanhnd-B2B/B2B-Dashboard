import pandas as pd
import sys
import io
import requests
import re
from datetime import datetime, time

sys.stdout.reconfigure(encoding='utf-8')

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
            
    if not ma_bac_1:
        continue
        
    if tinh not in province_mapping:
        province_mapping[tinh] = {}
        
    combo = (ma_bac_1, ma_bac_2)
    province_mapping[tinh][combo] = province_mapping[tinh].get(combo, 0) + row['SoLuongDon']

final_provinces = []
for tinh, combos in province_mapping.items():
    best_combo = max(combos.items(), key=lambda x: x[1])[0]
    final_provinces.append({
        'Tỉnh thành': tinh,
        'Mã bậc 1 (chữ cái)': best_combo[0],
        'Mã bậc 2 (số)': best_combo[1]
    })

df_prov = pd.DataFrame(final_provinces).sort_values('Tỉnh thành')

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
        h, min, s = m.groups()
        return time(int(h), int(min), int(s) if s else 0)
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
    
    if hub:
        routes_data.append({'Route': route, 'Hub': hub, 'Time': t_depart})

df_lv = pd.read_excel(xl2, sheet_name='LIÊN VÙNG')
for _, row in df_lv.iterrows():
    route = str(row.get('Tên tuyến')).strip()
    loc = str(row.get('Tên Kho (tóm tắt)')).lower()
    t_depart = parse_time(row.get('Giờ rời'))
    if route == 'nan' or t_depart is None: continue
    
    hub = None
    if loc.startswith('hưng yên') or 'hy_' in route.lower(): hub = 'HY'
    if loc.startswith('hà nội') or 'hn_' in route.lower() or 'đài tư' in loc: hub = 'HN'
        
    if hub:
        routes_data.append({'Route': route, 'Hub': hub, 'Time': t_depart})

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
    
    if hub:
        routes_data.append({'Route': route, 'Hub': hub, 'Time': t_depart})

df_routes = pd.DataFrame(routes_data)

# Add matching routes to provinces
def find_matching_routes(tinh):
    # simple match by stripping accents and matching part of string
    tinh_simp = tinh.lower().replace(' ', '').replace('đ', 'd').replace('ư', 'u').replace('ơ', 'o').replace('ô', 'o')
    matched = []
    for r in df_routes['Route'].unique():
        r_lower = r.lower().replace('đ', 'd')
        if tinh_simp in r_lower or (len(tinh.split()) > 1 and "".join([w[0] for w in tinh.lower().split()]) in r_lower):
             matched.append(r)
    
    return ", ".join(list(set(matched)))

df_prov['Mã chuyến cố định có thể xuất hàng'] = df_prov['Tỉnh thành'].apply(find_matching_routes)

# 3. BUILD ARTIFACT MARKDOWN
md = "# Báo Cáo Quy Hoạch Network B2B & Lịch Tải\n\n"

md += "## 1. Bảng Mã Sort & Mã Chuyến 63 Tỉnh Thành\n"
md += "| Tỉnh thành | Mã bậc 1 (chữ cái) | Mã bậc 2 (số) | Mã chuyến cố định có thể xuất hàng |\n"
md += "|---|---|---|---|\n"
for _, row in df_prov.iterrows():
    md += f"| {row['Tỉnh thành']} | **{row['Mã bậc 1 (chữ cái)']}** | {row['Mã bậc 2 (số)']} | {row['Mã chuyến cố định có thể xuất hàng']} |\n"

md += "\n\n## 2. Lịch Trình Chuyến Tải Theo Cung Giờ\n"
md += "| Cung Giờ | KTC Hưng Yên (HY01) | KTC Đài Tư (HN02) |\n"
md += "|---|---|---|\n"

timetable = {h: {'HY': set(), 'HN': set()} for h in range(24)}

for _, row in df_routes.iterrows():
    h = row['Time'].hour
    timetable[h][row['Hub']].add(row['Route'])

for h in range(24):
    h_next = (h + 1) % 24
    time_str = f"{h:02d}:00 - {h_next:02d}:00"
    hy_routes = "<br>".join(sorted(timetable[h]['HY'])) if timetable[h]['HY'] else "-"
    hn_routes = "<br>".join(sorted(timetable[h]['HN'])) if timetable[h]['HN'] else "-"
    md += f"| **{time_str}** | {hy_routes} | {hn_routes} |\n"

with open(r'C:\Users\admin\.gemini\antigravity\brain\69b75e67-7aa3-4208-86bf-145bc122fd1e\quy_hoach_b2b.md', 'w', encoding='utf-8') as f:
    f.write(md)
