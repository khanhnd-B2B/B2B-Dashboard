import pandas as pd
url = "https://docs.google.com/spreadsheets/d/1YNuLmUv6FRVMieyQy4JVnFscvkqnBdygzaWaQvOWMzU/export?format=csv&gid=0"
try:
    df = pd.read_csv(url, nrows=5)
    print("Success. Columns:")
    print(df.columns.tolist())
except Exception as e:
    print("Error:", e)
