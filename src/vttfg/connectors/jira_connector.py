# src/vttfg/connectors/jira_connector.py
import logging
import re
import requests
from typing import Optional, List, Dict
from ..models import JiraContext
from ..config import CONFIG
from datetime import datetime
from requests.auth import HTTPBasicAuth

logger = logging.getLogger("vttfg.jira")

_URL_RE = re.compile(r"https?://[^\s)>\"]+")

class JiraConnector:
    """
    Minimal JIRA REST connector.

    Requirements (from CONFIG / .env):
      - CONFIG.jira_base_url  (e.g. "https://yourcompany.atlassian.net")
      - CONFIG.jira_user      (username/email)
      - CONFIG.jira_api_token (API token)

    Behavior:
      - fetch_issue(jira_id) returns a JiraContext with title, description,
        comments (list of strings), linked_docs (list of URLs), attachments (list of dicts),
        created_at (datetime) and raw_payload (original JSON).
      - Raises RuntimeError if credentials / base_url missing.
      - Raises for HTTP errors with helpful logging.
    """
    def __init__(self, base_url: Optional[str] = None, user: Optional[str] = None, token: Optional[str] = None):
        self.base_url = (base_url or CONFIG.jira_base_url or "").rstrip("/")
        self.user = user or CONFIG.jira_user
        self.token = token or CONFIG.jira_api_token

        if not self.base_url:
            raise RuntimeError("JIRA_BASE_URL must be set in CONFIG / .env")
        if not (self.user and self.token):
            # In some setups a bearer token might be used; we still require at least token.
            raise RuntimeError("JIRA credentials missing: set JIRA_USER and JIRA_API_TOKEN in env")

        # Precompute auth object for requests
        self.auth = HTTPBasicAuth(self.user, self.token)

        # Standard headers
        self._headers = {"Accept": "application/json"}

    def _issue_url(self, issue_key: str) -> str:
        # Use fields param to limit returned data
        return f"{self.base_url}/rest/api/2/issue/{issue_key}?fields=summary,description,created,comment,attachment"

    def _comment_page(self, issue_key: str, start_at: int = 0, max_results: int = 50) -> Dict:
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}/comment?startAt={start_at}&maxResults={max_results}"
        resp = requests.get(url, auth=self.auth, headers=self._headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _extract_urls(self, text: Optional[str]) -> List[str]:
        if not text:
            return []
        return list({m.group(0) for m in _URL_RE.finditer(text)})

    def fetch_issue(self, jira_id: str) -> JiraContext:
        """
        Fetch a JIRA issue and return JiraContext.
        """
        run_ctx = {"run_id": "-", "step": "jira_fetch"}
        try:
            url = self._issue_url(jira_id)
            logger.info("Fetching JIRA issue %s from %s", jira_id, url, extra=run_ctx)
            r = requests.get(url, auth=self.auth, headers=self._headers, timeout=30)
            r.raise_for_status()
            payload = r.json()
            fields = payload.get("fields", {})

            title = fields.get("summary") or ""
            # description in JIRA can be either a string or structured content
            description = fields.get("description") or ""
            # created is ISO8601
            created_str = fields.get("created")
            created_at = None
            if created_str:
                try:
                    created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                except Exception:
                    try:
                        created_at = datetime.strptime(created_str, "%Y-%m-%dT%H:%M:%S.%f%z")
                    except Exception:
                        created_at = datetime.utcnow()

            # Comments: JIRA sometimes includes them in fields.comment.comments but pagination is safer
            comments_list: List[str] = []
            try:
                # Use paginated comment endpoint for robustness
                start = 0
                page_size = 50
                while True:
                    page = self._comment_page(jira_id, start_at=start, max_results=page_size)
                    for c in page.get("comments", []) or []:
                        body = c.get("body")
                        # body can be rich content in some setups; attempt to get plain text
                        if isinstance(body, dict):
                            # try common fields
                            text = body.get("content")
                            if not text:
                                text = str(body)
                            else:
                                # fallback: join text nodes
                                try:
                                    # naive flatten of Atlassian storage-format -> text
                                    def flatten_content(content):
                                        out = []
                                        if isinstance(content, list):
                                            for it in content:
                                                out.extend(flatten_content(it))
                                        elif isinstance(content, dict):
                                            if content.get("text"):
                                                out.append(content.get("text"))
                                            else:
                                                for v in content.values():
                                                    out.extend(flatten_content(v))
                                        elif isinstance(content, str):
                                            out.append(content)
                                        return out
                                    text = " ".join(flatten_content(text))
                                except Exception:
                                    text = str(body)
                        else:
                            text = str(body or "")
                        comments_list.append(text)
                    # paging
                    if page.get("isLast", False) or page.get("total", 0) <= (start + page_size):
                        break
                    start += page_size
            except requests.HTTPError as he:
                # non-fatal: log and continue
                logger.warning("Failed to fetch comments for %s: %s", jira_id, he, extra=run_ctx)

            # Attachments metadata
            attachments_meta: List[Dict] = []
            for a in fields.get("attachment", []) or []:
                try:
                    attachments_meta.append({
                        "filename": a.get("filename"),
                        "content_url": a.get("content"),
                        "mimeType": a.get("mimeType"),
                        "size": a.get("size"),
                    })
                except Exception:
                    continue

            # linked docs: extract URLs from description + comments
            linked_docs = set(self._extract_urls(description))
            for c in comments_list:
                for u in self._extract_urls(c):
                    linked_docs.add(u)

            jc = JiraContext(
                jira_id=jira_id,
                title=title,
                description=(description if isinstance(description, str) else str(description)),
                comments=comments_list,
                linked_docs=list(linked_docs),
                attachments=attachments_meta,
                created_at=created_at or datetime.utcnow(),
                raw_payload=payload
            )
            logger.info("Fetched JIRA %s: title=%s comments=%d attachments=%d linked_docs=%d",
                        jira_id, title, len(comments_list), len(attachments_meta), len(linked_docs),
                        extra=run_ctx)
            return jc
        except requests.HTTPError as e:
            # include response body if possible for debugging
            resp = getattr(e, "response", None)
            body = None
            try:
                if resp is not None:
                    body = resp.text
            except Exception:
                body = None
            logger.error("HTTP error fetching Jira %s: %s body=%s", jira_id, e, (body[:200] if body else None), extra=run_ctx)
            raise
        except Exception as e:
            logger.exception("Unexpected error fetching Jira %s: %s", jira_id, e, extra=run_ctx)
            raise
