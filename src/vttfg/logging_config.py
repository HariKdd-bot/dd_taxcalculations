# src/vttfg/logging_config.py
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from .config import CONFIG

LOG_DIR = os.getenv("VTTFG_OUTPUT_DIR", CONFIG.output_dir)
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "vttfg.log")

DEFAULT_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_SENSITIVE = os.getenv("LOG_SENSITIVE", "false").lower() in ("1", "true", "yes")

class ContextFilter(logging.Filter):
    """Attach minimal context if present in record.extra"""
    def filter(self, record):
        # Ensure run_id always exists for easier grepping
        if not hasattr(record, "run_id"):
            record.run_id = "-"
        if not hasattr(record, "step"):
            record.step = "-"
        return True

def setup_logging(level: str = DEFAULT_LEVEL):
    level_no = getattr(logging, level, logging.INFO)

    # root logger
    root = logging.getLogger()
    root.setLevel(level_no)

    # formatter: timestamp, level, run_id, step, message
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s run=%(run_id)s step=%(step)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    # console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level_no)
    ch.setFormatter(formatter)
    ch.addFilter(ContextFilter())

    # rotating file handler
    fh = RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    fh.setLevel(level_no)
    fh.setFormatter(formatter)
    fh.addFilter(ContextFilter())

    # Avoid duplicate handlers if already configured
    if not root.handlers:
        root.addHandler(ch)
        root.addHandler(fh)

    # lower-level noisy libs to WARNING by default
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    # expose config
    logging.getLogger(__name__).debug("Logging configured", extra={"run_id": "-", "step": "init"})
    return LOG_PATH, LOG_SENSITIVE
