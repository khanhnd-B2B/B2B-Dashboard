import pandas as pd
import json

file_path = 'd:\\LophocAI\\quanlyB2B\\20260520_112825.xlsx'
df = pd.read_excel(file_path, nrows=5)

info = {
    'columns': list(df.columns),
    'sample_data': df.to_dict(orient='records')
}

with open('d:\\LophocAI\\quanlyB2B\\schema.json', 'w', encoding='utf-8') as f:
    json.dump(info, f, ensure_ascii=False, indent=2)

print("Schema extracted.")
