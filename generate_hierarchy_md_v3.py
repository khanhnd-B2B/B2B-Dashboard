import pandas as pd
import sys
import os
import re
import requests
import io

sys.stdout.reconfigure(encoding='utf-8')

# 1. Parse sqllab file for accurate mapping
sqllab_path = r'd:\LophocAI\quanlyB2B\sqllab_untitled_query_49_20260712T190431.xlsx'
df_sql = pd.read_excel(sqllab_path)

def get_province_mapping():
    mapping = {}
    for _, row in df_sql.dropna(subset=['sort_code', 'TinhGiao']).iterrows():
        sc = str(row['sort_code']).upper()
        tinh = row['TinhGiao']
        parts = sc.split('-')
        for i, p in enumerate(parts):
            p = p.strip()
            if p.isalpha():
                if p not in mapping:
                    mapping[p] = {}
                prefix = parts[i-1].strip() if i > 0 else ""
                combo = f"{prefix}-{p}" if prefix else p
                if combo not in mapping[p]:
                    mapping[p][combo] = {}
                mapping[p][combo][tinh] = mapping[p][combo].get(tinh, 0) + row['SoLuongDon']
    
    final_mapping = {}
    for code, combos in mapping.items():
        final_mapping[code] = {}
        for combo, tinhs in combos.items():
            best_tinh = max(tinhs.items(), key=lambda x: x[1])[0]
            final_mapping[code][combo] = best_tinh
    return final_mapping

code_map = get_province_mapping()

def format_province(code):
    if code not in code_map:
        return "Không xác định"
    combos = code_map[code]
    
    # Filter combos: if it's a combo (contains '-'), the prefix MUST contain a number
    valid_combos = {}
    for combo, prov in combos.items():
        if '-' in combo:
            prefix = combo.split('-')[0]
            if any(c.isdigit() for c in prefix):
                valid_combos[combo] = prov
        else:
            valid_combos[combo] = prov
            
    if not valid_combos:
        valid_combos = combos # fallback
        
    provinces = list(set(valid_combos.values()))
    
    # If the code strongly represents ONE province (or if user wants single mapping for non-region)
    # Actually, we can check if it represents > 1 province
    if len(provinces) == 1:
        return provinces[0]
    else:
        # Group by province to show prefix -> province
        prov_to_prefixes = {}
        for combo, prov in valid_combos.items():
            if '-' in combo: # Only show xxx-CODE
                prov_to_prefixes.setdefault(prov, []).append(combo)
            else:
                # If there's a standalone code but it's a multi-province region, we can ignore the standalone one
                pass
                
        details = []
        for prov, prefixes in prov_to_prefixes.items():
            if prefixes:
                details.append(f"{', '.join(prefixes)} => {prov}")
            
        if details:
            return "Nhiều tỉnh (" + " | ".join(details) + ")"
        else:
            return ", ".join(provinces)

# 2. Get valid routes from URL 2
url2 = 'https://docs.google.com/spreadsheets/d/1_rqhL3OKNv5lYid3FkGtbWly7rXzfUVRbX_m1OrrEtc/export?format=xlsx'
valid_routes = {}
try:
    res2 = requests.get(url2)
    xl2 = pd.ExcelFile(io.BytesIO(res2.content))
    # Sheet 2: '6 TỈNH '
    df_6t = pd.read_excel(xl2, sheet_name='6 TỈNH ')
    if 'Mã chuyến' in df_6t.columns:
        for r in df_6t['Mã chuyến'].dropna().unique():
            valid_routes[str(r).strip()] = "Tuyến 6 Tỉnh"
            
    # Sheet 3: 'LIÊN VÙNG'
    df_lv = pd.read_excel(xl2, sheet_name='LIÊN VÙNG')
    if 'Tên tuyến' in df_lv.columns and 'Tên Kho (tóm tắt)' in df_lv.columns:
        for _, row in df_lv.dropna(subset=['Tên tuyến']).iterrows():
            valid_routes[str(row['Tên tuyến']).strip()] = str(row['Tên Kho (tóm tắt)']).strip()
            
    # Sheet 4: 'MIỀN BẮC'
    df_mb = pd.read_excel(xl2, sheet_name='MIỀN BẮC')
    if 'Tên tuyến' in df_mb.columns:
        for r in df_mb['Tên tuyến'].dropna().unique():
            valid_routes[str(r).strip()] = "Tuyến Miền Bắc"
except Exception as e:
    print("Error fetching URL2:", e)

# 3. Parse the pivot table
file_path = r'd:\LophocAI\quanlyB2B\file chia tuyến.xlsx'
df = pd.read_excel(file_path, sheet_name='Sheet3', skiprows=3, header=None)
df = df[[0, df.columns[-1]]]
df.columns = ['Code', 'Total']
df['Total'] = pd.to_numeric(df['Total'], errors='coerce')
df = df[df['Code'].notna()]
df = df[df['Code'] != 'Grand Total']

hierarchy = {}
current_parent = None

for _, row in df.iterrows():
    code = str(row['Code']).strip()
    total = row['Total']
    
    if '_' not in code and len(code) <= 3:
        current_parent = code
        hierarchy[current_parent] = {'total': total, 'children': []}
    else:
        if current_parent is not None:
            if 'blank' not in code.lower() and total > 0:
                hierarchy[current_parent]['children'].append((code, total))

# Internal hubs for exclusion
internal_nodes = {'HN', 'HY', 'ĐT', 'DX'}

def is_internal_route(route_code):
    parts = re.split(r'[_\\-]', route_code.upper())
    nodes = [p for p in parts if p.isalpha()]
    if not nodes:
        return False
    for n in nodes:
        if n not in internal_nodes:
            return False
    return True

md_content = "# Bảng Phân Tích Mã Tuyến Chính và Tỉnh Đại Diện (Cập nhật lần 3)\n\n"
md_content += "Dưới đây là danh sách các mã chính có tổng số lượng > 400.\n"
md_content += "- Các mã đại diện nhiều tỉnh (như C, HY) được liệt kê chi tiết `xxx - Mã => Tỉnh`. Các tiền tố lỗi (không chứa số) đã bị loại bỏ.\n"
md_content += "- Chú thích tên tuyến được lấy tự động từ danh sách URL bạn cung cấp.\n\n"

sorted_parents = sorted(hierarchy.items(), key=lambda x: x[1]['total'], reverse=True)

for parent, data in sorted_parents:
    if data['total'] > 400:
        province_desc = format_province(parent)
        md_content += f"### Mã **{parent}** (Tổng SL: {int(data['total']):,}) - Biểu thị: **{province_desc}**\n"
        md_content += "Các tuyến đi:\n"
        
        sorted_children = sorted(data['children'], key=lambda x: x[1], reverse=True)
        
        valid_children_count = 0
        for child_code, child_total in sorted_children:
            if is_internal_route(child_code):
                continue
                
            if child_total > 10:  # Lowered threshold to include more routes since user complained about missing routes
                desc = valid_routes.get(child_code, "")
                desc_str = f" *( {desc} )*" if desc and desc != "nan" else ""
                md_content += f"- {child_code}: {int(child_total):,}{desc_str}\n"
                valid_children_count += 1
                
        others = sum(1 for c, t in sorted_children if not is_internal_route(c) and t <= 10)
        if others > 0:
            md_content += f"- *(và {others} tuyến đi nhỏ lẻ khác)*\n"
            
        if valid_children_count == 0 and others == 0:
            # Check if there are internal routes
            internal_count = sum(1 for c, t in sorted_children if is_internal_route(c))
            if internal_count > 0:
                md_content += f"- *(Các tuyến thuộc mã này đều là luân chuyển nội bộ và đã bị loại trừ)*\n"
            else:
                md_content += "- *(Không có thông tin chi tiết tuyến trong Pivot Table)*\n"
            
        md_content += "\n---\n\n"

out_dir = r'C:\Users\admin\.gemini\antigravity\brain\69b75e67-7aa3-4208-86bf-145bc122fd1e'
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, 'chi_tiet_tuyen_ma_chinh_v3.md')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(md_content)

print(f"Successfully wrote artifact to {out_path}")
