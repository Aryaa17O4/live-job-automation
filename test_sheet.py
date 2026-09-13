import json, gspread, os
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

json_content = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
print("Secret length:", len(json_content))
print("First char:", repr(json_content[0]))

creds_dict = json.loads(json_content)
print("client_email:", creds_dict["client_email"])

creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
client = gspread.authorize(creds)
sheet_id = os.environ["GOOGLE_SHEET_ID"]
wb = client.open_by_key(sheet_id)
ws = wb.worksheet("Jobs")
ws.append_row(["2026-09-14 00:00", "Test", "Test Job", "Test Co", "Remote", "Scraped", "https://test.com"])
print("SUCCESS - row added!")
