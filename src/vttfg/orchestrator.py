# src/vttfg/orchestrator.py
"""
Main orchestrator with enhanced logging and run_id correlation.
"""
import logging, os, json, time
from .connectors.jira_connector import JiraConnector
from .connectors import filestore, snowflake_connector
from .connectors.llm_client import get_llm_client
from .extraction import extract_from_text
from .generator import read_template_metadata, generate_bci_from_template
from .rules_engine import apply_rules, populate_expected_rates
from .config import CONFIG
from .models import JiraContext
from datetime import datetime

# Setup logging config (calls setup in logging_config)
from .logging_config import setup_logging
LOG_PATH, LOG_SENSITIVE = setup_logging()
logger = logging.getLogger('vttfg.orchestrator')
from .prompts_loader import load_prompts

class Orchestrator:
    def __init__(self, jira_connector: JiraConnector = None, llm_client=None, sf_connector=None):
        self.jira = jira_connector or JiraConnector()
        self.llm = llm_client or get_llm_client()
        self.sf = sf_connector or snowflake_connector.SnowflakeConnector()

    def _log(self, level, msg, run_id='-', step='-', **extra):
        logger.log(level, msg, extra={"run_id": run_id, "step": step, **(extra or {})})

    def run_for_jira(self, jira_id: str, overrides: dict = None) -> dict:
        run_id = f"run_{int(datetime.utcnow().timestamp())}_{jira_id}"
        start_t = time.time()
        self._log(logging.INFO, f"Starting run for {jira_id}", run_id=run_id, step="start")

        # Step 1 - fetch JIRA context
        try:
            jc = self.jira.fetch_issue(jira_id)
            self._log(logging.DEBUG, "Fetched JIRA issue", run_id=run_id, step="fetch_jira", jira_id=jira_id)
        except Exception as e:
            self._log(logging.ERROR, f"Failed to fetch JIRA {jira_id}: {e}", run_id=run_id, step="fetch_jira")
            raise

        # Build text blob: title + description + comments + linked docs (avoid huge content in logs)
        parts = [jc.title or '', jc.description or ''] + (jc.comments or [])
        text_blob = '\n\n'.join([p if isinstance(p, str) else str(p) for p in parts])
        self._log(logging.INFO, "Built text blob", run_id=run_id, step="build_blob", blob_len=len(text_blob) if isinstance(text_blob, str) else -1)

        # Step 3 - classify
        try:
            prompts = load_prompts()
            prompts_classify = prompts["classification"]["prompt"]
            classification, conf = self.llm.classify(text_blob, prompt_override= prompts_classify)
            self._log(logging.INFO, f"LLM suggested classification={classification} conf={conf}", run_id=run_id, step="classify", classification=classification, confidence=conf)
        except Exception as e:
            self._log(logging.ERROR, f"LLM classification failed: {e}", run_id=run_id, step="classify")
            classification, conf = ("UC6", 0.0)

        # allow overrides from caller
        if overrides and overrides.get('classification'):
            self._log(logging.INFO, f"Overriding classification to {overrides.get('classification')}", run_id=run_id, step="override")
            classification = overrides.get('classification')

        # Step 4 - extract
        try:
            extraction = extract_from_text(text_blob, classification, jira_created_at=jc.created_at)
            # For safety, redact raw LLM output length in log; if LOG_SENSITIVE True we log more
            raw_len = len(extraction.raw_llm_response or "") if extraction.raw_llm_response else 0
            self._log(logging.INFO, "Extraction complete", run_id=run_id, step="extract", item_count=len(extraction.item_codes or []), divisions=len(extraction.division_codes or []), states=len(extraction.states or []), raw_len=raw_len)
            if LOG_SENSITIVE:
                self._log(logging.DEBUG, f"Raw LLM extraction: {extraction.raw_llm_response}", run_id=run_id, step="extract_raw")
        except Exception as e:
            self._log(logging.ERROR, f"Extraction failed: {e}", run_id=run_id, step="extract")
            raise

        # Step 5 - defaults & manual override (UI normally)
        template_path = overrides.get('template_path') if overrides and overrides.get('template_path') else CONFIG.bci_template_path
        template_meta = {}
        try:
            template_meta = read_template_metadata(template_path)
            self._log(logging.INFO, "Loaded template metadata", run_id=run_id, step="template_read", template_path=template_path, columns=len(template_meta.get('columns', [])))
        except Exception as e:
            self._log(logging.WARNING, f"Failed to read template metadata: {e}", run_id=run_id, step="template_read")

        division_map = template_meta.get('product_to_division', {})

        # Step 6 - rules & expand
        try:
            testrows = apply_rules(extraction, division_map=division_map)
            self._log(logging.INFO, "Rules engine expanded test rows", run_id=run_id, step="rules_expand", count=len(testrows))
        except Exception as e:
            self._log(logging.ERROR, f"Rules engine failed: {e}", run_id=run_id, step="rules_expand")
            raise

        # enforce caps
        if len(testrows) > CONFIG.max_combinations:
            self._log(logging.WARNING, f"Test rows {len(testrows)} > max_combinations {CONFIG.max_combinations}. Truncating.", run_id=run_id, step="cap")
            testrows = testrows[:CONFIG.max_combinations]

        # Step 7 - expected rate fetch
        try:
            testrows = populate_expected_rates(testrows, self.sf)
            missing = sum(1 for r in testrows if r.expected_tax_rate is None)
            self._log(logging.INFO, "Expected rates fetched", run_id=run_id, step="fetch_rates", missing_rates=missing)
        except Exception as e:
            self._log(logging.ERROR, f"Fetching expected rates failed: {e}", run_id=run_id, step="fetch_rates")
            raise

        # Step 8 - generate BCI file
        try:
            csv_bytes = generate_bci_from_template(template_path, testrows)
            file_name = f"vttfg_{jira_id}.csv"
            saved = filestore.save_bytes(file_name, csv_bytes)
            self._log(logging.INFO, "Generated BCI file saved", run_id=run_id, step="save", file_path=saved)
        except Exception as e:
            self._log(logging.ERROR, f"BCI generation failed: {e}", run_id=run_id, step="generate")
            raise

        # Step 9 - audit
        duration = time.time() - start_t
        result = {'file_path': saved, 'rows_count': len(testrows), 'metadata': {'run_id': run_id, 'classification': classification, 'duration_seconds': duration}}
        self._log(logging.INFO, f"Completed run in {duration:.1f}s", run_id=run_id, step="complete", rows=len(testrows), file_path=saved)
        return result



def load_classify_prompt():
    """
    Load classification prompt from prompts/classify.json relative to the project base.
    Works regardless of current working directory.
    """
    # Get absolute path to the project root (vttfg_project)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    prompt_path = os.path.join(base_dir, "prompts", "classify.json")

    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    with open(prompt_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("classification", {}).get("prompt")