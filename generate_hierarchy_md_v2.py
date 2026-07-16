import pandas as pd
import sys
import os
import re

sys.stdout.reconfigure(encoding='utf-8')

# 1. Parse sqllab file for accurate mapping
sqllab_path = r'd:\LophocAI\quanlyB2B\sqllab_untitled_query_49_20260712T190431.xlsx'
df_sql = pd.read_excel(sqllab_path)

# We want to map each letter to its provinces.
# Rule from user: 1 tỉnh chỉ tương ứng 1 chữ cái. 
# But for 'C' and 'HY' (and maybe 'A', 'D', 'E', 'G'), they represent multiple provinces via prefixes like 'xxx-C' or 'xxx-HY'.
# Let's extract the pattern xxx-CODE.
# Looking at sort_codes: 'C-209-C-09-00' -> '209-C', '89-HY-176-00' -> '89-HY'
# Actually, the user says "xxx - C => từng loại nó là gì" meaning we should list the prefix-code mapping.

def get_province_mapping():
    # We will look at all unique sort_codes and their TinhGiao
    mapping = {}
    
    for _, row in df_sql.dropna(subset=['sort_code', 'TinhGiao']).iterrows():
        sc = str(row['sort_code']).upper()
        tinh = row['TinhGiao']
        
        # Split by '-'
        parts = sc.split('-')
        
        # Find all alphabetic parts
        for i, p in enumerate(parts):
            p = p.strip()
            if p.isalpha():
                # It's a letter code like C, HY, M, NG...
                if p not in mapping:
                    mapping[p] = {}
                
                # If there's a prefix before it, capture it
                prefix = parts[i-1].strip() if i > 0 else ""
                
                # Tally the province for this prefix-code combo
                combo = f"{prefix}-{p}" if prefix else p
                
                if combo not in mapping[p]:
                    mapping[p][combo] = {}
                mapping[p][combo][tinh] = mapping[p][combo].get(tinh, 0) + row['SoLuongDon']
    
    # Resolve the most likely province for each combo
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
    # If there are many combos (like xxx-C), list them out
    # If there's only a few or one dominant one, simplify.
    # To keep it clean, let's just list the unique provinces this code represents.
    provinces = list(set(combos.values()))
    
    if len(provinces) == 1:
        return provinces[0]
    else:
        # User wants "xxx - C => Tỉnh" format for multi-province codes
        details = []
        # group by province to show prefix -> province
        prov_to_prefixes = {}
        for combo, prov in combos.items():
            prov_to_prefixes.setdefault(prov, []).append(combo)
            
        for prov, prefixes in prov_to_prefixes.items():
            details.append(f"{', '.join(prefixes)} => {prov}")
            
        return "Nhiều tỉnh (" + " | ".join(details) + ")"

# 2. Parse the pivot table
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

# Define internal hubs for exclusion
# Based on user: HY_HN, HY_ĐT, HY_DX are internal. 
# Internal nodes: HN, HY, ĐT, DX.
internal_nodes = {'HN', 'HY', 'ĐT', 'DX'}

def is_internal_route(route_code):
    # Split route code by '_' and '-'
    parts = re.split(r'[_\\-]', route_code.upper())
    # Extract only the alphabetic parts (nodes)
    nodes = [p for p in parts if p.isalpha()]
    
    if not nodes:
        return False
    
    # Check if ALL nodes are in the internal_nodes list
    for n in nodes:
        if n not in internal_nodes:
            return False
            
    # Also user said "chỉ có các điểm này trong cùng 1 tên mã chuyến thôi nhé. Ví dụ có HY - HN - M => thì là khác"
    # The above logic exactly checks this. If there is an 'M', it will return False.
    return True

md_content = "# Bảng Phân Tích Mã Tuyến Chính và Tỉnh Đại Diện (Cập nhật)\n\n"
md_content += "Dưới đây là danh sách các mã chính có tổng số lượng > 400.\n"
md_content += "- Các tuyến **luân chuyển nội bộ** (chỉ gồm HN, HY, ĐT, DX) đã được **loại bỏ**.\n"
md_content += "- Các mã đại diện nhiều tỉnh (như C, HY) được chi tiết hóa theo cấu trúc `xxx - Mã => Tỉnh`.\n\n"

sorted_parents = sorted(hierarchy.items(), key=lambda x: x[1]['total'], reverse=True)

for parent, data in sorted_parents:
    if data['total'] > 400:
        province_desc = format_province(parent)
        md_content += f"### Mã **{parent}** (Tổng SL: {int(data['total']):,}) - Biểu thị: **{province_desc}**\n"
        md_content += "Các tuyến đi:\n"
        
        sorted_children = sorted(data['children'], key=lambda x: x[1], reverse=True)
        
        valid_children_count = 0
        for child_code, child_total in sorted_children:
            # Check for internal route
            if is_internal_route(child_code):
                continue
                
            if child_total > 50:
                md_content += f"- {child_code}: {int(child_total):,}\n"
                valid_children_count += 1
                
        # Count remaining small valid routes
        others = sum(1 for c, t in sorted_children if not is_internal_route(c) and t <= 50)
        if others > 0:
            md_content += f"- *(và {others} tuyến đi nhỏ lẻ khác)*\n"
            
        if valid_children_count == 0 and others == 0:
            md_content += "- *(Chỉ có luân chuyển nội bộ hoặc không có tuyến)*\n"
            
        md_content += "\n---\n\n"

out_dir = r'C:\Users\admin\.gemini\antigravity\brain\69b75e67-7aa3-4208-86bf-145bc122fd1e'
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, 'chi_tiet_tuyen_ma_chinh_v2.md')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(md_content)

print(f"Successfully wrote artifact to {out_path}")
