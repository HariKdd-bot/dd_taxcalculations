import json, os

def load_prompt_file(path):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        key = next(iter(data.keys()))
        return data[key].get("prompt")
    except Exception:
        return None

def load_classify_prompt():
    here = os.path.join(os.path.dirname(__file__), "..", "..", "prompts", "classify.json")
    return load_prompt_file(here)

def load_prompt_for(use_case):
    here = os.path.join(os.path.dirname(__file__), "..", "..", "prompts", f"{use_case}.json")
    return load_prompt_file(here)
