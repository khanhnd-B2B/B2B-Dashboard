import pandas as pd
import datetime
import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

SPREADSHEET_ID = '1YNuLmUv6FRVMieyQy4JVnFscvkqnBdygzaWaQvOWMzU'
RANGE_NAME = 'DATASORTING'
MASTER_FILE = 'Data B2B Master.xlsx'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

print(f'[{datetime.datetime.now()}] Start fetching data from Google Sheets API...')

try:
    if not os.path.exists('token.json'):
        print('ERROR: token.json not found')
        exit(1)
        
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if creds and creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request
        creds.refresh(Request())
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])
    
    if not values:
        print('ERROR: Sheet is empty or data not found.')
    else:
        df_new = pd.DataFrame(values[1:], columns=values[0])
        print(f'Fetched {len(df_new)} new rows.')
        
        df_master = pd.read_excel(MASTER_FILE)
        df_combined = pd.concat([df_master, df_new], ignore_index=True)
        
        if 'MaDonGoc' in df_combined.columns:
            before_len = len(df_combined)
            df_combined = df_combined.drop_duplicates(subset=['MaDonGoc'], keep='last')
            after_len = len(df_combined)
            print(f'Removed {before_len - after_len} duplicate rows.')
            
        df_combined.to_excel(MASTER_FILE, index=False)
        print('Update complete!')
except Exception as e:
    print(f'ERROR: {str(e)}')
