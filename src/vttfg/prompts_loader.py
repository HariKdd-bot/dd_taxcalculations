"""
Utility to load all prompt definitions (classification + extraction)
from prompts.json stored in the project root.
"""

import os
import json
import logging
from .logging_config import setup_logging

LOG_PATH, LOG_SENSITIVE = setup_logging()
logger = logging.getLogger("vttfg.prompts")


def load_prompts():
    """
    Load the central prompts.json file.

    Resolves path relative to the project root (vttfg_project/prompts/prompts.json).
    Returns a dictionary of all prompt definitions, injecting default values
    for classification if needed.
    """
    # Compute absolute project root, two levels above this file.
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    prompt_path = os.path.join(base_dir, "prompts", "prompts.json")

    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompts file not found: {prompt_path}")

    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Merge meta default into classification.prompt if present.
        meta_default = data.get("meta", {}).get("default_classify_prompt", "")
        cls_prompt = data.get("classification", {}).get("prompt", "")
        if "{meta_default}" in cls_prompt:
            data["classification"]["prompt"] = cls_prompt.replace("{meta_default}", meta_default)

        logger.debug("Loaded prompts from %s", prompt_path, extra={"run_id": "-", "step": "prompts_load"})
        return data
    except Exception as e:
        logger.error("Failed to load prompts.json: %s", e, extra={"run_id": "-", "step": "prompts_load"})
        raise
