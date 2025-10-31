#!/usr/bin/env python3
"""
vttfg CLI (corrected): builds full text context (JIRA + linked docs) before classifying.

Usage:
    python src/vttfg/cli.py --jira DD-1001
Or interactive:
    python src/vttfg/cli.py
"""
import os
import sys
import json
import argparse
import logging
import traceback
from pathlib import Path
from typing import Optional


# Ensure project src is importable when launching from project root
THIS_FILE = Path(__file__).resolve()
SRC_PARENT = str(THIS_FILE.parent.parent)  # project_root/src
if SRC_PARENT not in sys.path:
    sys.path.insert(0, SRC_PARENT)

# Imports from the project
try:
    from vttfg.orchestrator import Orchestrator
    from vttfg.prompts_loader import load_prompts
    from vttfg.extraction import extract_from_text
    from vttfg.config import CONFIG
    from vttfg.connectors.jira_connector import JiraConnector
except Exception:
    print("Failed to import vttfg modules. Ensure you're running from project root and code is present.")
    traceback.print_exc()
    sys.exit(1)

# Optional connectors
_google_docs_available = False
try:
    from vttfg.connectors.google_docs_connector import GoogleDocsConnector  # optional
    _google_docs_available = True
except Exception:
    _google_docs_available = False

# CLI logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("vttfg.cli")


def tail_log(log_path: str, lines: int = 200) -> str:
    if not os.path.exists(log_path):
        return f"[No log file found at {log_path}]"
    with open(log_path, "r", encoding="utf-8", errors="ignore") as fh:
        all_lines = fh.readlines()
    return "".join(all_lines[-lines:])


def prompt_json_from_input(prompt_msg: str):
    """
    Ask the user to provide JSON either by path or by pasting.
    Return parsed dict or None.
    """
    print(prompt_msg)
    choice = input("Enter 'file' to load from file, 'paste' to paste JSON, or ENTER to skip: ").strip().lower()
    if choice == "file":
        p = input("Path to JSON file: ").strip()
        if not p:
            raise ValueError("No path provided")
        with open(os.path.expanduser(p), "r", encoding="utf-8") as fh:
            return json.load(fh)
    elif choice == "paste":
        print("Paste JSON now. End with a blank line:")
        lines = []
        while True:
            try:
                ln = input()
            except EOFError:
                break
            if ln.strip() == "" and lines:
                break
            lines.append(ln)
        txt = "\n".join(lines)
        return json.loads(txt)
    else:
        return None


def fetch_linked_docs_text(linked_docs, google_conn: Optional[object] = None):
    """
    Given a list of linked doc URLs, attempt to fetch text for each.
    Tries GoogleDocsConnector if available; otherwise returns URLs as text placeholders.
    Returns concatenated text and a dict of {url: preview_text}.
    """
    out_map = {}
    texts = []
    if not linked_docs:
        return "", out_map
    for url in linked_docs:
        try:
            if _google_docs_available and google_conn:
                # connector should implement fetch_text(url) -> str
                txt = google_conn.fetch_text(url)
                preview = (txt[:1000] + "...") if txt and len(txt) > 1000 else (txt or "")
                out_map[url] = preview
                texts.append(txt or "")
            else:
                # fallback: include the URL and a short note
                out_map[url] = f"[URL included for context: {url}]"
                texts.append(f"Linked document: {url}")
        except Exception as e:
            logger.warning("Failed to fetch linked doc %s: %s", url, e)
            out_map[url] = f"[Failed to fetch: {e}]"
            texts.append(f"Linked document (failed fetch): {url}")
    return "\n\n".join(texts), out_map


def build_text_blob_from_jira(jc, google_conn=None):
    """
    Build a single text blob for LLM that includes:
      - title
      - description
      - comments
      - fetched linked doc text (if available) OR the URLs
    """
    pieces = []
    if getattr(jc, "title", None):
        pieces.append(f"Title: {jc.title}")
    if getattr(jc, "description", None):
        pieces.append("Description:\n" + (jc.description if isinstance(jc.description, str) else str(jc.description)))
    if getattr(jc, "comments", None):
        comments_text = "\n\n".join([f"Comment {i+1}:\n{(c if isinstance(c,str) else str(c))}" for i, c in enumerate(jc.comments)])
        if comments_text:
            pieces.append("Comments:\n" + comments_text)
    # linked docs
    linked_docs = getattr(jc, "linked_docs", []) or []
    doc_text, doc_map = fetch_linked_docs_text(linked_docs, google_conn=google_conn)
    if doc_text:
        pieces.append("Linked documents content:\n" + doc_text)
    elif linked_docs:
        pieces.append("Linked documents:\n" + "\n".join(linked_docs))
    # attachments metadata (do not download)
    attachments = getattr(jc, "attachments", []) or []
    if attachments:
        att_lines = []
        for a in attachments:
            fn = a.get("filename") if isinstance(a, dict) else str(a)
            att_lines.append(f"- attachment: {fn}")
        pieces.append("Attachments:\n" + "\n".join(att_lines))
    return "\n\n".join(pieces), doc_map


def show_csv_head(path: str, n: int = 10):
    import csv
    if not os.path.exists(path):
        print(f"[CSV not found: {path}]")
        return
    with open(path, newline='', encoding='utf-8') as fh:
        r = csv.reader(fh)
        for i in range(n):
            try:
                row = next(r)
            except StopIteration:
                break
            print(i + 1, row)


def cli_main(args):
    orc = Orchestrator()
    prompts = None
    try:
        prompts = load_prompts()
    except Exception as e:
        logger.warning("Could not load prompts.json: %s", e)

    # Set up optional GoogleDocsConnector if available (no hard failure)
    google_conn = None
    if _google_docs_available:
        try:
            google_conn = GoogleDocsConnector()
            logger.info("GoogleDocsConnector initialized for linked doc fetching")
        except Exception as e:
            logger.warning("GoogleDocsConnector present but failed to init: %s", e)

    jira_id = args.jira or input("Enter JIRA ID (e.g. DD-1001): ").strip()
    if not jira_id:
        print("No JIRA ID provided. Exiting.")
        return

    # Optional prompt override input
    prompt_override_text = None
    if prompts:
        resp = input("Use default classification prompt from prompts.json? (Y/n) ")
        if resp.strip().lower() in ("n", "no"):
            choice = input("Enter 'file' to load prompt file, 'paste' to paste prompt, or ENTER to use default: ").strip().lower()
            if choice == "file":
                p = input("Classification prompt file path: ").strip()
                try:
                    with open(p, "r", encoding="utf-8") as fh:
                        prompt_override_text = fh.read()
                except Exception as e:
                    print("Failed to read file:", e)
                    prompt_override_text = None
            elif choice == "paste":
                print("Paste the classification prompt. End with blank line:")
                lines = []
                while True:
                    ln = input()
                    if ln.strip() == "" and lines:
                        break
                    lines.append(ln)
                prompt_override_text = "\n".join(lines)

    # Fetch JIRA context
    print(f"\nFetching JIRA {jira_id} ...")
    try:
        jc = orc.jira.fetch_issue(jira_id)
    except Exception:
        logger.exception("Failed to fetch JIRA issue")
        print("Failed to fetch JIRA; aborting.")
        return

    # Build text blob with linked docs content if possible
    text_blob, doc_map = build_text_blob_from_jira(jc, google_conn=google_conn)
    logger.debug("Built text blob length=%d", len(text_blob))

    # Get classification prompt
    classify_prompt = prompt_override_text or (prompts.get("classification", {}).get("prompt") if prompts else None)

    # Call LLM classification ONCE with full context
    print("\nCalling LLM classification (using ticket text + linked docs) ...")
    try:
        classification, conf = orc.llm.classify(text_blob, classify_prompt)
        print(f"LLM suggested: {classification} (confidence={conf})")
    except Exception:
        logger.exception("LLM classify failed")
        print("LLM classification failed; using fallback UC6")
        classification, conf = ("UC6", 0.0)

    # Human override
    user_choice = input("Accept suggestion? (Y/n) or enter new classification (UC2/UC3/UC4/UC6/Maintenance): ").strip()
    if user_choice == "" or user_choice.lower() in ("y", "yes"):
        chosen_class = classification
    elif user_choice.upper() in ("UC2", "UC3", "UC4", "UC6", "MAINTENANCE"):
        chosen_class = user_choice.upper()
    else:
        chosen_class = input("Enter classification (UC2/UC3/UC4/UC6/Maintenance): ").strip()

    print(f"Using classification: {chosen_class}")
    print("\n--- Text blob sent to LLM classification (truncated) ---")
    print(text_blob[:500] + ("\n..." if len(text_blob) > 500 else ""))
    file_path = "/Users/harinadh.kunapareddy/Downloads/vttfg_project/output/output.txt"

# Write the text blob into the file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text_blob)
    # Extraction preview (LLM.extract) using chosen_class unless manual override is provided
    print("\nExtraction preview:")
    try:
        extraction = extract_from_text(text_blob, chosen_class, jira_created_at=jc.created_at)
        print(" - item_codes:", extraction.item_codes)
        print(" - product_classes:", extraction.product_classes)
        print(" - states:", extraction.states)
        print(" - postal_codes:", extraction.postal_codes)
        print(" - date_specs:", extraction.date_specs)
        print(" - flex_fields:", extraction.flex_fields)
    except Exception:
        logger.exception("Extraction failed")
        print("LLM extraction failed; you can provide manual extraction JSON.")
        extraction = None

    # Offer manual extraction override
    manual_extraction = None
    ans = input("Provide manual extraction JSON to override LLM extraction? (y/N) ").strip().lower()
    if ans == "y":
        try:
            manual_extraction = prompt_json_from_input("Provide manual extraction JSON (file or paste):")
            print("Manual extraction loaded.")
        except Exception:
            logger.exception("Failed to parse manual extraction JSON")
            print("Manual extraction not used.")

    # Ask for confirmation to generate BCI
    confirm = input("Proceed to generate BCI CSV? (y/N) ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return

    # Prepare overrides
    overrides = {"classification": chosen_class}
    if manual_extraction:
        overrides["manual_extraction"] = manual_extraction

    # Optional template override
    tpl = input(f"Enter template path (or ENTER to use default {CONFIG.bci_template_path}): ").strip()
    if tpl:
        overrides["template_path"] = tpl

    print("\nRunning Orchestrator (this will generate the BCI CSV)...")
    try:
        result = orc.run_for_jira(jira_id, overrides=overrides)
        print("Orchestrator finished. Result summary:")
        print(json.dumps(result, indent=2))
        file_path = result.get("file_path")
        if file_path and os.path.exists(file_path):
            print("\nGenerated CSV path:", file_path)
            print("\nCSV preview (first 20 rows):")
            show_csv_head(file_path, n=20)
        else:
            print("No CSV created or file not found.")
    except Exception:
        logger.exception("Orchestration failed")
        print("Orchestration failed; see traceback above.")
    finally:
        # tail the run log
        log_path = os.path.join(CONFIG.output_dir, "vttfg.log")
        print("\nRecent logs (tail):")
        print(tail_log(log_path, lines=200))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="VTTFG CLI (debug-friendly)")
    p.add_argument("--jira", help="JIRA ID to process", default=None)
    args = p.parse_args()
    try:
        cli_main(args)
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
        sys.exit(1)
