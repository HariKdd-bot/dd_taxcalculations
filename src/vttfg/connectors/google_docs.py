import logging, re
from ..config import CONFIG
logger = logging.getLogger("vttfg.gdocs")

def fetch_doc_text(url: str) -> str:
    if not CONFIG.google_credentials:
        raise RuntimeError("GOOGLE_CREDENTIALS_JSON not set in .env")
    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
    except Exception as e:
        logger.exception("google client libs not installed")
        raise RuntimeError("google-api-python-client and google-auth required") from e
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    if not m:
        return f"[Unsupported document URL: {url}]"
    doc_id = m.group(1)
    creds = service_account.Credentials.from_service_account_file(CONFIG.google_credentials, scopes=["https://www.googleapis.com/auth/documents.readonly"])
    service = build("docs", "v1", credentials=creds)
    doc = service.documents().get(documentId=doc_id).execute()
    content = []
    for el in doc.get("body", {}).get("content", []):
        if "paragraph" in el:
            for run in el["paragraph"].get("elements", []):
                txt = run.get("textRun", {}).get("content")
                if txt:
                    content.append(txt)
    return "\n".join(content)
