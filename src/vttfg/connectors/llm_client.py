"""
LLM client using the Portkey SDK (portkey_ai).

This module *only* uses the portkey_ai SDK as the primary LLM gateway.
If the SDK is missing or initialization fails, a Mock client is returned
(for local development/testing) — there is NO HTTP fallback here by design.

Exposed API:
- get_llm_client() -> client with .classify(ticket_text, prompt_override=None) and
                      .extract(ticket_text, classification, prompt_override=None)
"""
from __future__ import annotations
import json
import re
import logging
from typing import Tuple, Optional, Any, Dict

from ..config import CONFIG
from ..logging_config import setup_logging

LOG_PATH, LOG_SENSITIVE = setup_logging()
logger = logging.getLogger("vttfg.llm")

# Regex helpers to find JSON blocks
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.S | re.I)
_BRACE_RE = re.compile(r"(\{(?:.|\n)*\})", re.S)


def _safe_parse_json(text: Optional[str]) -> Optional[dict]:
    """Try JSON loads on whole text, fenced JSON blocks, or first {...} ... returns dict or None."""
    if not text or not isinstance(text, str):
        return None
    s = text.strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    m = _JSON_BLOCK_RE.search(s)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    for m in _BRACE_RE.finditer(s):
        try:
            return json.loads(m.group(1))
        except Exception:
            continue
    return None


class PortkeySdkClient:
    """
    Portkey SDK client wrapper.

    Requires:
      - CONFIG.portkey_virtual_key (virtual key)
      - CONFIG.portkey_base_url (optional; SDK accepts base_url)
      - CONFIG.portkey_model (defaults in config)
    """
    def __init__(self, base_url: Optional[str] = None, virtual_key: Optional[str] = None, model: Optional[str] = None):
        try:
            from portkey_ai import Portkey  # dynamic import
        except Exception as e:
            logger.exception("portkey_ai import failed", extra={"run_id": "-", "step": "llm_init"})
            raise RuntimeError("portkey_ai SDK not installed") from e

        self.base_url = (base_url or CONFIG.portkey_base_url).rstrip("/")
        self.virtual_key = virtual_key or CONFIG.portkey_virtual_key
        self.model = model or CONFIG.portkey_model

        if not self.virtual_key:
            raise RuntimeError("PORTKEY_VIRTUAL_KEY must be set for PortkeySdkClient")

        try:
            # Construct Portkey client (we pass api_key=None and virtual_key)
            # The SDK's constructor may accept base_url and virtual_key as shown in examples.
            self.client = Portkey(api_key=None, virtual_key=self.virtual_key, base_url=self.base_url)
            logger.info("Portkey SDK client initialized", extra={"run_id": "-", "step": "llm_init"})
        except Exception as e:
            logger.exception("Failed to instantiate Portkey SDK client", extra={"run_id": "-", "step": "llm_init"})
            raise

    def _coerce_text(self, resp: Any) -> str:
        """Return a string representation of SDK response for logging/parsing fallback."""
        try:
            if isinstance(resp, (dict, list)):
                return json.dumps(resp)
            return str(resp)
        except Exception:
            return ""

    def _extract_content(self, resp: Any) -> str:
        """
        Heuristically extract content from SDK response shapes:
          - dicts with choices -> choices[0].message.content or choices[0].text
          - SDK objects with .choices attribute
          - fallback to stringifying response
        """
        try:
            # dict-like common shape
            if isinstance(resp, dict):
                choices = resp.get("choices")
                if isinstance(choices, list) and len(choices) > 0:
                    first = choices[0]
                    if isinstance(first, dict):
                        msg = first.get("message") or {}
                        if isinstance(msg, dict) and "content" in msg:
                            return msg.get("content") or ""
                        if isinstance(first.get("text"), str):
                            return first.get("text")
                return json.dumps(resp)
            # object-like SDK response
            if hasattr(resp, "choices"):
                try:
                    choices = getattr(resp, "choices")
                    if choices and len(choices) > 0:
                        first = choices[0]
                        # try message.content attribute
                        if hasattr(first, "message") and getattr(first, "message") and hasattr(getattr(first, "message"), "content"):
                            return getattr(first, "message").content
                        return str(first)
                except Exception:
                    pass
        except Exception:
            pass
        return self._coerce_text(resp)

    def _call_completion(self, messages: list, max_tokens: int = 800, temperature: float = 0.0) -> Any:
        """Call Portkey SDK chat completion and return raw SDK response."""
        try:
            prompt_len = sum(len(str(m.get("content", ""))) for m in messages if isinstance(m, dict))
            logger.debug("Portkey SDK request prepared (model=%s prompt_len=%d)", self.model, prompt_len, extra={"run_id": "-", "step": "llm_request"})
        except Exception:
            pass

        resp = self.client.chat.completions.create(messages=messages, model=self.model, max_tokens=max_tokens, temperature=temperature)
        try:
            txt = self._coerce_text(resp)
            logger.debug("Portkey SDK responded (len=%d)", len(txt), extra={"run_id": "-", "step": "llm_response"})
        except Exception:
            logger.debug("Portkey SDK responded", extra={"run_id": "-", "step": "llm_response"})
        return resp

    def classify(self, ticket_text: str, prompt_override: Optional[str] = None) -> Tuple[str, float]:
        """
        Ask Portkey to classify the ticket into UC2/UC3/UC4/UC6/Maintenance.
        Returns (classification, confidence).
        """
        prompt = (prompt_override or 'Return JSON: {"classification":"UC2|UC3|UC4|UC6|Maintenance","confidence":0.0}') + "\nTicket:\n" + (ticket_text or "")
        messages = [{"role": "user", "content": prompt}]
        try:
            raw = self._call_completion(messages, max_tokens=200, temperature=0.0)
            content = self._extract_content(raw)
            parsed = _safe_parse_json(content)
            if parsed and isinstance(parsed, dict):
                cls = parsed.get("classification", "UC6")
                conf = float(parsed.get("confidence", 0.0) or 0.0)
                logger.debug("Portkey classify parsed result: %s (conf=%s)", cls, conf, extra={"run_id": "-", "step": "llm_parse"})
                return cls, conf
        except Exception as e:
            logger.warning("Portkey SDK classify call failed: %s", str(e), extra={"run_id": "-", "step": "llm_request_error"})

        # heuristics fallback (sane default)
        t = (ticket_text or "").lower()
        if "merchant" in t:
            return "UC2", 0.9
        if "mpf" in t or "marketplace" in t:
            return "UC3", 0.9
        if "fee" in t:
            return "UC4", 0.8
        if "tax" in t:
            return "UC6", 0.7
        return "UC6", 0.5

    def extract(self, ticket_text: str, classification: str, prompt_override: Optional[str] = None) -> Dict[str, Any]:
        """
        Ask Portkey to extract fields (product codes, division, states, dates, flex fields, etc.)
        Returns a parsed dict (or a fallback minimal structure).
        """
        prompt = (prompt_override or "") + "\nTicket:\n" + (ticket_text or "")
        messages = [{"role": "user", "content": prompt}]
        try:
            raw = self._call_completion(messages, max_tokens=800, temperature=0.0)
            content = self._extract_content(raw)
            parsed = _safe_parse_json(content)
            if parsed and isinstance(parsed, dict):
                logger.debug("Portkey extract parsed keys=%s", list(parsed.keys()), extra={"run_id": "-", "step": "llm_parse"})
                return parsed
        except Exception as e:
            logger.warning("Portkey SDK extract call failed: %s", str(e), extra={"run_id": "-", "step": "llm_request_error"})

        # fallback minimal structure
        logger.info("Using default extraction fallback (no parsed output)", extra={"run_id": "-", "step": "llm_fallback"})
        return {
            "item_codes": [CONFIG.default_item],
            "product_classes": [],
            "division_codes": [],
            "department_codes": [],
            "postal_codes": [],
            "states": [],
            "date_specs": [{"type": "effective", "date": None}],
            "flex_fields": {},
            "confidence": 0.0,
            "raw_extracted_text": ticket_text[:1000],
        }


# Factory
def get_llm_client():
    """
    Returns:
      - PortkeySdkClient if portkey_ai is installed and initialization succeeds.
      - Otherwise, a Mock client that supports classify(...) and extract(...).
    """
    try:
        client = PortkeySdkClient(base_url=CONFIG.portkey_base_url, virtual_key=CONFIG.portkey_virtual_key, model=CONFIG.portkey_model)
        logger.info("Using Portkey SDK client", extra={"run_id": "-", "step": "llm_init"})
        return client
    except Exception as e:
        logger.warning("Portkey SDK client init failed: %s. Falling back to Mock.", str(e), extra={"run_id": "-", "step": "llm_init"})

    # Mock client
    class Mock:
        def classify(self, t: str, p: Optional[str] = None) -> Tuple[str, float]:
            logger.info("Mock LLM classify used", extra={"run_id": "-", "step": "llm_mock"})
            return ("UC6", 0.6)

        # def extract(self, t: str, c: str, p: Optional[str] = None) -> Dict[str, Any]:
        #     logger.info("Mock LLM extract used", extra={"run_id": "-", "step": "llm_mock"})
        #     return {
        #         "item_codes": [CONFIG.default_item],
        #         "product_classes": [],
        #         "division_codes": [],
        #         "department_codes": [],
        #         "postal_codes": [],
        #         "states": [],
        #         "date_specs": [{"type": "effective", "date": None}],
        #         "flex_fields": {},
        #         "confidence": 0.0,
        #         "raw_extracted_text": t[:1000],
        #     }

    return Mock()
