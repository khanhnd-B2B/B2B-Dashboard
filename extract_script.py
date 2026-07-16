import pandas as pd
import sys
sys.stdout.reconfigure(encoding="utf-8")

file_path = r"d:\LophocAI\quanlyB2B\file chia tuyến.xlsx"
df = pd.read_excel(file_path, sheet_name="Sheet3", skiprows=3, header=None)
df = df[[0, df.columns[-1]]]
df.columns = ["Code", "Total"]

df["Total"] = pd.to_numeric(df["Total"], errors="coerce")
filtered_df = df[(df["Total"] > 400) & (df["Code"].notna())]
filtered_df = filtered_df[filtered_df["Code"] != "Grand Total"]
filtered_df = filtered_df.sort_values(by="Total", ascending=False)

print(f"\nFound {len(filtered_df)} codes with Total > 400:")
for _, row in filtered_df.iterrows():
    print(f"{row['Code']}: {int(row['Total']):,}")
