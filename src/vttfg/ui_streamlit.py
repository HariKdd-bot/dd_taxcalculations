# src/vttfg/ui_streamlit.py
import os
import sys
import json
import pandas as pd
import streamlit as st

# Ensure src/ is on sys.path so package imports work when running:
# streamlit run src/vttfg/ui_streamlit.py
THIS_FILE = os.path.abspath(__file__)
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(THIS_FILE), ".."))  # src/
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from vttfg.orchestrator import Orchestrator
from vttfg.extraction import extract_from_text
from vttfg.prompts_loader import load_prompts
from vttfg.config import CONFIG
from vttfg.connectors.jira_connector import JiraConnector

st.set_page_config(page_title="VTTFG - Vertex Tax Test File Generator", layout="wide")
st.title("Vertex Tax Test File Generator (VTTFG) — Human-in-the-loop Classification")

orc = Orchestrator()
prompts = load_prompts()

st.markdown(
    """
    **Workflow**
    1. Enter JIRA ID and fetch suggestion (LLM classifies & extracts).
    2. Review suggested classification and extracted facts.
    3. If needed, override classification and preview extraction again.
    4. Generate final BCI CSV (Orchestrator will run with your classification override).
    """
)

col1, col2 = st.columns([1, 2])

with col1:
    jira_id = st.text_input("JIRA ID", value="DD-1001")
    template_path = st.text_input("BCI template path (optional)", value=CONFIG.bci_template_path)
    btn_fetch = st.button("Fetch & Suggest")

with col2:
    st.write("Suggested classification will appear here after you click *Fetch & Suggest*.")

# Placeholders
suggestion_ph = st.empty()
extraction_ph = st.empty()
preview_ph = st.empty()
generate_ph = st.empty()

if btn_fetch and jira_id.strip():
    with st.spinner("Fetching JIRA and running LLM classification..."):
        # 1) Fetch JIRA
        try:
            jc = orc.jira.fetch_issue(jira_id)
        except Exception as e:
            st.error(f"Failed to fetch JIRA {jira_id}: {e}")
            raise

        # Build text blob
        parts = [jc.title or "", jc.description or ""] + (jc.comments or [])
        text_blob = "\n\n".join([p if isinstance(p, str) else str(p) for p in parts])

        # 2) LLM classification suggestion (single call)
        classify_prompt = prompts.get("classification", {}).get("prompt")
        try:
            suggested_class, confidence = orc.llm.classify(text_blob, prompt_override=classify_prompt)
        except Exception as e:
            st.error(f"LLM classification failed: {e}")
            suggested_class, confidence = ("UC6", 0.0)

        # 3) Show suggestion and allow override
        suggestion_ph.subheader("LLM Suggested Classification")
        suggestion_ph.write(f"**Suggested:** `{suggested_class}` — confidence `{confidence:.2f}`")
        choices = ["UC2", "UC3", "UC4", "UC6", "Maintenance"]
        # default to suggested_class if in choices else first
        default_idx = choices.index(suggested_class) if suggested_class in choices else 0
        chosen_class = st.selectbox("Confirm or change classification", options=choices, index=default_idx)

        # 4) Show extraction preview for suggested_class
        try:
            extraction = extract_from_text(text_blob, suggested_class, jira_created_at=jc.created_at)
        except Exception as e:
            st.error(f"LLM extraction (suggested) failed: {e}")
            extraction = None

        extraction_ph.subheader("LLM Extraction (for suggested classification)")
        if extraction:
            try:
                # show JSON pretty
                extraction_json = {
                    "classification_used_for_extract": suggested_class,
                    "confidence": extraction.confidence,
                    "item_codes": extraction.item_codes,
                    "product_classes": extraction.product_classes,
                    "division_codes": extraction.division_codes,
                    "department_codes": extraction.department_codes,
                    "postal_codes": extraction.postal_codes,
                    "states": extraction.states,
                    "date_specs": extraction.date_specs,
                    "flex_fields": extraction.flex_fields,
                }
                extraction_ph.json(extraction_json)
            except Exception:
                extraction_ph.write(str(extraction))

        # 5) If user changed classification, preview extraction under chosen_class
        if chosen_class != suggested_class:
            st.info(f"You changed classification from `{suggested_class}` to `{chosen_class}` — re-running extraction with `{chosen_class}` now.")
            try:
                extraction_override = extract_from_text(text_blob, chosen_class, jira_created_at=jc.created_at)
                extraction_override_json = {
                    "classification_used_for_extract": chosen_class,
                    "confidence": extraction_override.confidence,
                    "item_codes": extraction_override.item_codes,
                    "product_classes": extraction_override.product_classes,
                    "division_codes": extraction_override.division_codes,
                    "department_codes": extraction_override.department_codes,
                    "postal_codes": extraction_override.postal_codes,
                    "states": extraction_override.states,
                    "date_specs": extraction_override.date_specs,
                    "flex_fields": extraction_override.flex_fields,
                }
                extraction_ph.subheader("LLM Extraction (for chosen classification)")
                extraction_ph.json(extraction_override_json)
            except Exception as e:
                st.error(f"LLM extraction (chosen classification) failed: {e}")

        # 6) Provide button to generate final BCI with override
        if st.button("Generate BCI using chosen classification"):
            with st.spinner("Running orchestration with your classification..."):
                try:
                    overrides = {"classification": chosen_class, "template_path": template_path}
                    result = orc.run_for_jira(jira_id, overrides=overrides)
                except Exception as e:
                    st.error(f"Orchestration failed: {e}")
                    raise

                # Show results (file path and preview)
                file_path = result.get("file_path")
                rows_count = result.get("rows_count", 0)
                st.success(f"Generated {rows_count} rows — saved to `{file_path}`")

                # Try to show CSV preview
                try:
                    df = pd.read_csv(file_path)
                    preview_ph.subheader("Generated BCI Preview (first 200 rows)")
                    preview_ph.dataframe(df.head(200))
                    # Provide download button (read bytes)
                    csv_bytes = df.to_csv(index=False).encode("utf-8")
                    st.download_button("Download generated CSV", csv_bytes, file_name=os.path.basename(file_path), mime="text/csv")
                except Exception as e:
                    st.warning(f"Could not preview generated CSV: {e}")
                    st.write(f"Saved file: `{file_path}`")

else:
    st.info("Choose 'Other (JIRA-driven)' and click **Fetch & Suggest** to start.")
