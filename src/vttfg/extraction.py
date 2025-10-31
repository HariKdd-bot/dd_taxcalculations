import logging
from .connectors.llm_client import get_llm_client
from .prompts import PROMPTS
from .config import CONFIG
from .models import ExtractionResult
from datetime import datetime
from vttfg.prompts_loader import load_prompts

logger = logging.getLogger('vttfg.extraction')
_llm = get_llm_client()
def extract_from_text(text: str, classification: str, jira_created_at: datetime = None) -> ExtractionResult:
    prompts=load_prompts()
    prompt = prompts.get("uc3", {}).get("prompt") if prompts else None

    # prompt = PROMPTS.get(classification, {}).get('extraction_prompt')
    logger.debug("Calling LLM.extract for classification=%s prompt_len=%d", classification, len(prompt or ''), extra={"run_id":"-","step":"extract_call"})
    try:
        raw = _llm.extract(text, classification, prompt_override=prompt) if hasattr(_llm, 'extract') else _llm.extract(text, classification)
    except Exception as e:
        logger.error("LLM.extract raised: %s", e, extra={"run_id":"-","step":"extract_error"})
        raw = None
    if not raw or not isinstance(raw, dict):
        raw = {'product_codes':[CONFIG.default_item], 'product_classes':[], 'division_codes':[], 'department_codes':[], 'postal_codes':[], 'states':[], 'date_specs':[{'type':'effective','date': jira_created_at.date().isoformat() if jira_created_at else datetime.utcnow().date().isoformat()}], 'flex_fields':{}, 'confidence':0.0, 'raw_extracted_text': text[:1000]}
        logger.info("Using default extraction fallback", extra={"run_id":"-","step":"extract_fallback"})
    logger.debug("Extraction raw keys=%s", list(raw.keys()) if isinstance(raw, dict) else 'raw', extra={"run_id":"-","step":"extract_return"})
    return ExtractionResult(
        classification=classification,
        item_codes=[str(x).upper() for x in (raw.get('product_codes') or raw.get('item_codes') or [])],
        product_classes=raw.get('product_classes') or [],
        division_codes=[str(x).upper() for x in (raw.get('division_codes') or [])],
        department_codes=[str(x).upper() for x in (raw.get('department_codes') or [])],
        postal_codes=raw.get('postal_codes') or [],
        states=[str(x).upper() for x in (raw.get('states') or [])],
        date_specs=raw.get('date_specs') or [],
        taxability_matrix=raw.get('taxability_matrix'),
        category_mapping=raw.get('category_mapping'),
        flex_fields=raw.get('flex_fields') or {},
        confidence=float(raw.get('confidence', 0.0)),
        raw_llm_response=str(raw.get('raw_extracted_text') or str(raw))
    )
