import os, logging, json, datetime
from vttfg.config import CONFIG
from vttfg.logging_config import setup_logging
from vttfg.prompts_loader import load_classify_prompt, load_prompt_for
from vttfg.llm import get_llm_client
from vttfg.connectors import jira as jira_conn, google_docs as gdocs, google_sheets as gsheets, snowflake as snowconn
from vttfg.validators import validate_uc3
from vttfg.rules import build_testrows
from vttfg.generator import rows_to_csv_bytes

LOG_PATH, _ = setup_logging(CONFIG.output_dir)
logger = logging.getLogger("vttfg.orchestrator")

class Orchestrator:
    def __init__(self):
        self.llm = get_llm_client()
        self.jira = jira_conn
        self.gdocs = gdocs
        self.gsheets = gsheets
        try:
            self.snow = snowconn.SnowflakeConnector()
        except Exception as e:
            logger.warning("Snowflake connector not available: %s", e)
            self.snow = None

    def run_for_jira(self, jira_id, overrides=None):
        overrides = overrides or {}
        run_id = f"run_{int(datetime.datetime.utcnow().timestamp())}"
        debug = {"notes": []}
        # 1) Jira context (fetch once)
        jc = overrides.get("jira_context")
        if not jc:
            jc = self.jira.fetch_issue(jira_id)
        # 2) Build text blob (title + description + comments + linked docs text if any)
        pieces = []
        if getattr(jc, "title", None):
            pieces.append(f"Title: {jc.title}")
        if getattr(jc, "description", None):
            pieces.append("Description:\n" + (jc.description if isinstance(jc.description, str) else str(jc.description)))
        if getattr(jc, "comments", None):
            comments_text = "\n\n".join([str(c) for c in (jc.comments or [])])
            if comments_text:
                pieces.append("Comments:\n" + comments_text)
        # linked docs fetch
        linked_docs = getattr(jc, "linked_docs", []) or []
        for url in linked_docs:
            try:
                txt = self.gdocs.fetch_doc_text(url)
                pieces.append("Linked doc content:\n" + txt[:2000])
            except Exception as e:
                logger.warning("Failed fetching linked doc %s: %s", url, e)
                pieces.append(f"Linked doc (url included): {url}")
        text_blob = overrides.get("text_blob") or "\n\n".join(pieces)
        # 3) Classification (LLM) once unless override
        classification = overrides.get("classification")
        if not classification:
            classify_prompt = load_classify_prompt()
            classification, conf = self.llm.classify(jc.title, prompt=classify_prompt)
        # 4) Extraction (LLM) unless manual override
        extraction = overrides.get("manual_extraction")
        if not extraction:
            prompt = load_prompt_for("uc3")
            extraction = self.llm.extract(text_blob, classification, prompt=prompt)
        # Ensure jira_created_at present if dates missing
        if "date_specs" not in extraction or not extraction.get("date_specs"):
            extraction["jira_created_at"] = jc.created_at.strftime("%Y-%m-%d") if jc and getattr(jc, "created_at", None) else ""
        # 5) Validate and collect questions
        qs = validate_uc3(extraction)
        if qs:
            debug["clarify_questions"] = qs
        # 6) Build test rows
        test_rows = build_testrows(extraction, template_path=overrides.get("template_path"))
        # 7) Optional expected rate fetch via Snowflake
        if self.snow:
            try:
                queries = []
                for r in test_rows:
                    queries.append((r.product_code, r.dest_main_division, r.dest_postal_code, r.document_date))
                rates = self.snow.batch_get_expected_rates(queries)
                for r in test_rows:
                    key = (r.product_code, r.dest_main_division, r.dest_postal_code, r.document_date)
                    if key in rates:
                        r.expected_value = rates[key]
            except Exception as e:
                logger.warning("Failed to fetch rates: %s", e)
        # 8) Generate CSV bytes and save
        csv_bytes = rows_to_csv_bytes(test_rows)
        os.makedirs(CONFIG.output_dir, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        fname = f"vttfg_bci_{jira_id.replace('/','_')}_{ts}.csv"
        out_path = os.path.join(CONFIG.output_dir, fname)
        with open(out_path, "wb") as fh:
            fh.write(csv_bytes)
        audit = {"jira_id": jira_id, "extraction": extraction, "debug": debug}
        audit_path = os.path.join(CONFIG.output_dir, f"audit_{jira_id}_{ts}.json")
        with open(audit_path, "w", encoding="utf-8") as fh:
            json.dump(audit, fh, default=str, indent=2)
        return {"rows_count": len(test_rows), "file_path": out_path, "audit_path": audit_path, "debug": debug}
