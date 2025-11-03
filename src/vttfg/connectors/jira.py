import requests, logging, re
from ..config import CONFIG
from ..models import JiraContext
logger = logging.getLogger("vttfg.jira")

def fetch_issue(issue_key: str) -> JiraContext:
    if not CONFIG.jira_base_url or not CONFIG.jira_user or not CONFIG.jira_api_token:
        raise RuntimeError("JIRA credentials not set in .env")
    base = CONFIG.jira_base_url.rstrip("/")
    url = f"{base}/rest/api/3/issue/{issue_key}?expand=renderedFields,changelog"
    resp = requests.get(url, auth=(CONFIG.jira_user, CONFIG.jira_api_token), timeout=30)
    resp.raise_for_status()
    data = resp.json()
    fields = data.get("fields", {})
    title = fields.get("summary") or ""
    # description may be object; coerce to string
    desc = fields.get("description") or ""
    if isinstance(desc, dict):
        desc = str(desc)
    comments = []
    for c in fields.get("comment", {}).get("comments", []):
        body = c.get("body") if isinstance(c.get("body"), str) else str(c.get("body"))
        comments.append(body)
    urls = re.findall(r"https?://\\S+", str(desc))
    return JiraContext(jira_id=issue_key, title=title, description=desc, comments=comments, linked_docs=urls, raw_payload=data)
