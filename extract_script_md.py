import pandas as pd
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

file_path = r'd:\LophocAI\quanlyB2B\file chia tuyến.xlsx'
df = pd.read_excel(file_path, sheet_name='Sheet3', skiprows=3, header=None)
df = df[[0, df.columns[-1]]]
df.columns = ['Code', 'Total']

df['Total'] = pd.to_numeric(df['Total'], errors='coerce')
filtered_df = df[(df['Total'] > 400) & (df['Code'].notna())]
filtered_df = filtered_df[filtered_df['Code'] != 'Grand Total']
filtered_df = filtered_df.sort_values(by='Total', ascending=False)

def is_main_code(code):
    return '_' not in str(code)

main_codes = filtered_df[filtered_df['Code'].apply(is_main_code)]
detail_codes = filtered_df[~filtered_df['Code'].apply(is_main_code)]

md_content = '# Tổng hợp Bảng Mã Chính (Sản lượng > 400)\n\n'
md_content += 'Dưới đây là danh sách tổng hợp các mã tuyến có tổng sản lượng lớn hơn 400 từ `file chia tuyến.xlsx`.\n\n'

md_content += '## 1. Các Mã Nhóm/Vùng Chính\n'
md_content += '| Mã | Tổng Sản Lượng |\n|---|---:|\n'
for _, row in main_codes.iterrows():
    md_content += f"| **{row['Code']}** | {int(row['Total']):,} |\n"

md_content += '\n## 2. Các Mã Tuyến Chi Tiết\n'
md_content += '| Mã Tuyến | Tổng Sản Lượng |\n|---|---:|\n'
for _, row in detail_codes.iterrows():
    md_content += f"| {row['Code']} | {int(row['Total']):,} |\n"

out_dir = r'C:\Users\admin\.gemini\antigravity\brain\69b75e67-7aa3-4208-86bf-145bc122fd1e'
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, 'bang_ma_chinh_tuyen.md')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(md_content)

print(f'Successfully wrote artifact to {out_path}')
