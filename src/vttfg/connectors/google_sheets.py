import logging, re
from ..config import CONFIG
logger = logging.getLogger("vttfg.gsheets")

def fetch_sheet_table(url_or_id: str):
    if not CONFIG.google_credentials:
        raise RuntimeError("GOOGLE_CREDENTIALS_JSON not set in .env")
    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
    except Exception as e:
        logger.exception("google client libs not installed")
        raise RuntimeError("google-api-python-client and google-auth required") from e
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url_or_id)
    sheet_id = m.group(1) if m else url_or_id
    creds = service_account.Credentials.from_service_account_file(CONFIG.google_credentials, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets().values().get(spreadsheetId=sheet_id, range="Sheet1").execute()
    values = sheet.get("values", [])
    if not values:
        return []
    headers = values[0]
    rows = []
    for row in values[1:]:
        obj = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
        rows.append(obj)
    return rows
