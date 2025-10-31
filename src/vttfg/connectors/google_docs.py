import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("vttfg.gdocs")


def fetch_doc_text(url: str) -> str:
    """
    Mock implementation to fetch document text.

    Behavior:
      - If `url` looks like a local file path (exists on disk), read & return file contents.
      - Otherwise return a deterministic mock string so callers can still function in tests.

    Args:
        url: Document URL or local file path.

    Returns:
        Document text as a string.
    """
    url = (url or "").strip()
    logger.info("fetch_doc_text called for %s", url, extra={"run_id": "-", "step": "gdocs_fetch"})

    if not url:
        logger.warning("Empty URL passed to fetch_doc_text")
        return ""

    # If the caller passed a local file path, read it and return its contents.
    # Accept either "file:///path/to/file" or plain path strings.
    try:
        if url.startswith("file://"):
            path = Path(url[len("file://") :])
        else:
            path = Path(url)

        if path.exists() and path.is_file():
            try:
                text = path.read_text(encoding="utf-8")
                logger.debug("Read %d characters from %s", len(text), path)
                return text
            except Exception as e:
                logger.exception("Failed to read local file %s: %s", path, e)
                # fall through to returning mock text

    except Exception:
        # Defensive: any unexpected Path processing error should not crash the mock
        logger.exception("Error while attempting to interpret url as file: %s", url)

    # Default mock return for non-file URLs
    return f"[MOCK DOC TEXT for {url}]"


def extract_tables_from_doc(url: str) -> List[List[List[str]]]:
    """
    Mock implementation to extract tables from a (Google) doc.

    Behavior:
      - If `url` refers to a local text file, attempt to parse simple ASCII pipe-delimited tables
        (lines containing '|' are interpreted as table rows).
      - Otherwise returns an empty list (no tables), or the found tables when parsing succeeds.

    Return format:
      - A list of tables.
      - Each table is a list of rows.
      - Each row is a list of cell strings.

    Examples:
      [
        [ ["col1", "col2"], ["val1", "val2"] ],   # table 1
        [ ["h1","h2","h3"], ["a","b","c"] ]       # table 2
      ]

    Args:
        url: Document URL or local file path.

    Returns:
        List of parsed tables (possibly empty).
    """
    logger.info("extract_tables_from_doc called for %s", url, extra={"run_id": "-", "step": "gdocs_tables"})
    text = fetch_doc_text(url)
    if not text:
        return []

    tables: List[List[List[str]]] = []
    current_table: List[List[str]] = []
    for line in text.splitlines():
        # Heuristic: treat lines that contain pipe '|' as table rows (common markdown/ASCII style)
        if "|" in line:
            # split on '|' and strip whitespace; ignore empty leading/trailing cells caused by pipes at ends
            cells = [cell.strip() for cell in line.split("|")]
            # Remove empty leading/trailing if they result from surrounding pipes
            if cells and cells[0] == "":
                cells = cells[1:]
            if cells and cells[-1] == "":
                cells = cells[:-1]
            if any(c for c in cells):  # skip all-empty rows
                current_table.append(cells)
        else:
            # treat blank line or non-table line as table separator
            if current_table:
                tables.append(current_table)
                current_table = []

    # append last table if present
    if current_table:
        tables.append(current_table)

    # If no pipe-style tables found, try to detect simple tab-delimited or comma-separated "tables"
    if not tables:
        # look for lines that have multiple tabs or commas consistently
        lines = [ln for ln in text.splitlines() if ln.strip()]
        if not lines:
            return []

        # crude detection: check first 30 lines for presence of tabs or commas
        tab_rows = [l for l in lines[:30] if "\t" in l]
        comma_rows = [l for l in lines[:30] if "," in l]
        if len(tab_rows) >= 2:
            # parse tab-delimited as a single table
            parsed = [[cell.strip() for cell in l.split("\t")] for l in lines if "\t" in l]
            if parsed:
                tables.append(parsed)
        elif len(comma_rows) >= 2:
            parsed = [[cell.strip() for cell in l.split(",")] for l in lines if "," in l]
            if parsed:
                tables.append(parsed)

    logger.debug("extract_tables_from_doc found %d table(s) in %s", len(tables), url)
    return tables
