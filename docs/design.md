# VTTFG Design Summary

See the architecture plan in the conversation. This document lists the main modules and responsibilities.

- Phase 1: Foundation & Data Flow
- Phase 2: Intelligence & Orchestration (LLM classification/extraction, rules engine)
- Phase 3: Generation & UI (CSV/Streamlit)

Connectors are mockable and clearly separated. To move to production:
- Implement Snowflake connector using `snowflake.connector`
- Implement LLM wrapper using OpenAI or the internal LLM API
- Add Google Docs/Drive connector using `google-api-python-client` and OAuth2
