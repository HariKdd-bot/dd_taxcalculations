# Implementation Guide

This repository is a skeleton. Follow these steps to implement production features:

1. Implement JiraConnector.fetch_issue to call Jira Cloud API and parse renderedFields.
2. Implement Google Docs/Sheets connectors using service account JSON.
3. Replace SnowflakeConnector.batch_get_expected_rates with real Snowflake queries (use temp tables for large batches).
4. Improve LLM prompts in prompts.py and tune max_tokens/temperature.
5. Implement robust template metadata extraction in generator.read_template_metadata.
6. Implement rules_engine.apply_rules: fuzzy matching, dedupe, caps, combination scoring.
7. Add human-in-loop UI screens in ui_streamlit for editing extraction results and approving expansions.
8. Add logging and audit writes in orchestrator in more detail.

Refer to docs/ARCHITECTURE_LOW_LEVEL.md for module interfaces.
