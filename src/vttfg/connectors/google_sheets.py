import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("vttfg.gsheets")


def _is_google_sheets_url(url: str) -> bool:
    """Rudimentary check whether the URL looks like a Google Sheets URL."""
    if not url:
        return False
    u = url.strip().lower()
    return "docs.google.com/spreadsheets" in u or u.startswith("gsheets://") or u.startswith("gsheet://")


def fetch_sheet_as_df(url: str, range_name: Optional[str] = None):
    """
    Mock/utility to fetch a "sheet" as a pandas DataFrame.

    Behavior:
      - If `url` refers to a local file:
          * .csv/.txt -> uses pandas.read_csv (auto-detects delimiter if possible)
          * .tsv -> pandas.read_csv(sep='\\t')
          * .xls/.xlsx -> pandas.read_excel (supports `range_name` as sheet name)
          * plain .txt with pipe-delimited tables will be parsed
      - If `url` looks like a Google Sheets URL, this function will NOT call the Google API;
        instead it returns an empty DataFrame and logs an explanatory message (mock behavior).
      - If `range_name` is provided and the file is an Excel workbook, `range_name` is treated as sheet name.
        For CSV/TSV/text files `range_name` is ignored.

    Args:
        url: Local file path or (mock) Google Sheets URL.
        range_name: Optional sheet name or A1-like descriptor (basic support only).

    Returns:
        pandas.DataFrame: the parsed sheet (may be empty).
    """
    import pandas as pd

    url = (url or "").strip()
    logger.info(
        "fetch_sheet_as_df called for %s range=%s",
        url,
        range_name,
        extra={"run_id": "-", "step": "gsheets_fetch"},
    )

    if not url:
        logger.warning("Empty URL/path passed to fetch_sheet_as_df; returning empty DataFrame")
        return pd.DataFrame()

    # If it's a Google Sheets URL, we don't attempt network calls in this mock.
    if _is_google_sheets_url(url):
        logger.warning(
            "Detected Google Sheets URL (%s). This mock does not fetch remote sheets; returning empty DataFrame.",
            url,
        )
        return pd.DataFrame()

    # Try treating url as a local file path
    try:
        path = Path(url)
        # Support file:// URLs
        if url.startswith("file://"):
            path = Path(url[len("file://") :])

        if not path.exists():
            logger.warning("Local file not found: %s. Returning empty DataFrame.", path)
            return pd.DataFrame()

        suffix = path.suffix.lower()

        # Excel files: allow range_name to specify sheet_name
        if suffix in (".xls", ".xlsx", ".xlsm", ".xlsb"):
            sheet_name = range_name if range_name else 0
            try:
                df = pd.read_excel(path, sheet_name=sheet_name)
                # If sheet_name returned dict (multiple sheets), pick the first
                if isinstance(df, dict):
                    first_key = next(iter(df.keys()))
                    df = df[first_key]
                return df
            except Exception:
                logger.exception("Failed to read Excel file %s", path)
                return pd.DataFrame()

        # CSV / TSV / TXT: attempt to detect delimiter or parse common ones
        if suffix in (".csv", ".txt", ".tsv"):
            # Read a small sample to guess delimiter
            try:
                sample = path.read_text(4096, encoding="utf-8", errors="replace")
            except Exception:
                sample = ""
            # Heuristics for delimiter
            if "\t" in sample and sample.count("\t") >= 1:
                sep = "\t"
            elif "|" in sample and sample.count("|") >= 1:
                sep = "|"
            elif "," in sample and sample.count(",") >= 1:
                sep = ","
            else:
                sep = ","  # fallback

            try:
                df = pd.read_csv(path, sep=sep)
                return df
            except Exception:
                logger.exception("pandas.read_csv failed for %s with sep=%r; returning empty DataFrame", path, sep)
                return pd.DataFrame()

        # Unknown extension: try generic read_csv first, then read_text->parse pipes
        try:
            df = pd.read_csv(path)
            return df
        except Exception:
            # try pipe-delimited parsing fallback
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
                lines = [ln for ln in text.splitlines() if "|" in ln]
                if lines:
                    rows = [[c.strip() for c in ln.split("|") if c.strip() != ""] for ln in lines]
                    if rows:
                        return pd.DataFrame(rows[1:], columns=rows[0] if len(rows[0]) == len(rows[1]) else None)
            except Exception:
                logger.exception("Fallback parsing failed for %s", path)

    except Exception:
        logger.exception("Unhandled error while attempting to load %s", url)

    # Last resort: return empty DataFrame
    logger.debug("Returning empty DataFrame for %s", url)
    return pd.DataFrame()
