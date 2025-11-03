import logging
from vttfg.config import CONFIG
from vttfg.logging_config import setup_logging

LOG_PATH, _ = setup_logging(CONFIG.output_dir)
logger = logging.getLogger("vttfg.llm")

def _extract_text_from_sdk_resp(resp):
    # Portkey SDK responses vary; coerce to string content
    try:
        if isinstance(resp, dict):
            choices = resp.get("choices")
            if isinstance(choices, list) and choices:
                first = choices[0]
                if isinstance(first, dict):
                    msg = first.get("message") or {}
                    if isinstance(msg, dict) and "content" in msg:
                        return msg["content"]
                    if "text" in first:
                        return first["text"]
            return str(resp)
        # object-like response
        return str(resp)
    except Exception:
        return str(resp)

class PortkeyClient:
    def __init__(self):
        try:
            from portkey_ai import Portkey
        except Exception as e:
            logger.exception("portkey_ai import failed")
            raise RuntimeError("portkey_ai SDK required") from e
        if not CONFIG.portkey_virtual_key:
            raise RuntimeError("PORTKEY_VIRTUAL_KEY not set in env")
        self.client = Portkey(api_key=None, virtual_key=CONFIG.portkey_virtual_key, base_url=CONFIG.portkey_base_url)
        self.model = CONFIG.portkey_model

    def classify(self, text, prompt=None):
        prompt = prompt or 'Return JSON: {"classification":"UC2|UC3|UC4|UC6|Maintenance","confidence":0.0}'
        messages = [{"role":"user","content": prompt + "\n\nTicket:\n" + (text or "")}]
        resp = self.client.chat.completions.create(messages=messages, model=self.model, max_tokens=200, temperature=0.0)
        import json
        resp_json = json.loads(str(resp))
        txt = _extract_text_from_sdk_resp(resp_json)
        try:
            j = json.loads(txt)
            return j.get("classification", "UC6"), float(j.get("confidence", 0.0) or 0.0)
        except Exception:
            t = (text or "").lower()
            if "merchant" in t: return "UC2", 0.9
            if "mpf" in t or "marketplace" in t: return "UC3", 0.9
            if "fee" in t: return "UC4", 0.8
            if "tax" in t: return "UC6", 0.7
            return "UC6", 0.5

    def extract(self, text, classification, prompt=None):
        messages = [{"role":"user","content": (prompt or "") + "\n\nTicket:\n" + (text or "")}]
        resp = self.client.chat.completions.create(messages=messages, model=self.model, max_tokens=800, temperature=0.0)
        import json
        resp_json = json.loads(str(resp))
        txt = _extract_text_from_sdk_resp(resp_json)
        import json
        try:
            j = json.loads(txt)
            return j
        except Exception:
            logger.warning("LLM returned non-json output during extract; returning minimal structure")
            return {
                "item_codes": [], "product_classes": [], "states": [], "postal_codes": [],
                "date_specs": [], "flex_fields": {}, "taxability_matrix": [], "category_mapping": [],
                "confidence": 0.0, "raw_extracted_text": (text or "")[:1000]
            }

def get_llm_client():
    return PortkeyClient()
