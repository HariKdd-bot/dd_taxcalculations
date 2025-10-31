from .connectors.llm_client import get_llm_client
llm = get_llm_client()
def classify_text(text: str):
    t = (text or '').lower()
    if 'merchant' in t:
        return 'UC2', 0.9
    if 'marketplace' in t or 'mpf' in t:
        return 'UC3', 0.9
    if 'fee' in t:
        return 'UC4', 0.8
    if 'tax' in t:
        return 'UC6', 0.7
    try:
        return llm.classify(text)
    except Exception:
        return 'UC6', 0.5
