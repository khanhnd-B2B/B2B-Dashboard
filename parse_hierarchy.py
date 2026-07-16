import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

# 1. Map Parent Code to Province using sqllab file
sqllab_path = r'd:\LophocAI\quanlyB2B\sqllab_untitled_query_49_20260712T190431.xlsx'
df_sql = pd.read_excel(sqllab_path)

def map_province(code):
    # Search for exactly this code as a component in sort_code
    # e.g., if code is NG, look for NG separated by hyphens or at ends
    mask = df_sql['sort_code'].fillna('').str.contains(rf'\b{code}\b', case=False, regex=True)
    if mask.any():
        return df_sql[mask]['TinhGiao'].mode()[0]
    return "Unknown"

# Build mapping for some examples
test_codes = ['NG', 'C', 'HY', 'W']
for c in test_codes:
    print(f"{c} -> {map_province(c)}")

# 2. Parse the pivot table
file_path = r'd:\LophocAI\quanlyB2B\file chia tuyến.xlsx'
df = pd.read_excel(file_path, sheet_name='Sheet3', skiprows=3, header=None)
df = df[[0, df.columns[-1]]]
df.columns = ['Code', 'Total']

df['Total'] = pd.to_numeric(df['Total'], errors='coerce')
# Remove NaN codes
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
            hierarchy[current_parent]['children'].append((code, total))

# Example output for NG
if 'NG' in hierarchy:
    print("\n--- NG ---")
    print(hierarchy['NG'])

print(f"\nTotal parents found: {len(hierarchy)}")
