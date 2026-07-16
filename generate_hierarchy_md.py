import pandas as pd
import sys
import os
import re

sys.stdout.reconfigure(encoding='utf-8')

# 1. Map Parent Code to Province using sqllab file
sqllab_path = r'd:\LophocAI\quanlyB2B\sqllab_untitled_query_49_20260712T190431.xlsx'
df_sql = pd.read_excel(sqllab_path)

def map_province(code):
    # Regex to find exact match of code, e.g., 'C' but not inside another word.
    mask = df_sql['sort_code'].fillna('').str.contains(rf'\b{re.escape(code)}\b', case=False, regex=True)
    if mask.any():
        return df_sql[mask]['TinhGiao'].mode()[0]
    return "Không xác định"

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
    
    # Simple heuristic: parent codes are short / don't contain underscore
    if '_' not in code and len(code) <= 3:
        current_parent = code
        hierarchy[current_parent] = {'total': total, 'children': []}
    else:
        if current_parent is not None:
            # exclude meaningless children like (blank) or NaN
            if 'blank' not in code.lower() and total > 0:
                hierarchy[current_parent]['children'].append((code, total))

# 3. Generate Markdown Content
md_content = "# Bảng Phân Tích Mã Tuyến Chính và Tỉnh Đại Diện\n\n"
md_content += "Dưới đây là danh sách các mã chính có tổng số lượng > 400. Mỗi mã chính sẽ bao gồm tỉnh đại diện và các tuyến xe đi kèm.\n\n"

# Sort parents by total descending
sorted_parents = sorted(hierarchy.items(), key=lambda x: x[1]['total'], reverse=True)

for parent, data in sorted_parents:
    if data['total'] > 400:
        province = map_province(parent)
        md_content += f"### Mã **{parent}** (Tổng SL: {int(data['total']):,}) - Biểu thị của tỉnh: **{province}**\n"
        md_content += "Các tuyến đi:\n"
        
        # Sort children descending
        sorted_children = sorted(data['children'], key=lambda x: x[1], reverse=True)
        
        # Filter children - e.g., display top routes or all routes
        for child_code, child_total in sorted_children:
            if child_total > 50: # Only show routes with meaningful volume (>50) to avoid clutter, or we can show all. 
                                 # Based on user's screenshot, they showed down to ~400. Let's show > 50.
                md_content += f"- {child_code}: {int(child_total):,}\n"
        
        # Count others if we thresholded
        others = sum(1 for c, t in sorted_children if t <= 50)
        if others > 0:
            md_content += f"- *(và {others} tuyến nhỏ lẻ khác)*\n"
            
        md_content += "\n---\n\n"

out_dir = r'C:\Users\admin\.gemini\antigravity\brain\69b75e67-7aa3-4208-86bf-145bc122fd1e'
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, 'chi_tiet_tuyen_ma_chinh.md')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(md_content)

print(f"Successfully wrote artifact to {out_path}")
