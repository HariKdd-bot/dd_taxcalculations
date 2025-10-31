# VTTFG - Low Level Architecture

This file describes the modules, classes, data models, and interfaces in the code base.

## Modules (short)
- config.py: environment-driven configuration (dataclass CONFIG)
- models.py: dataclasses for JiraContext, ExtractionResult, TestRow
- connectors/: Jira, Google Docs, Google Sheets, Snowflake, GeoNames, Filestore, LLM client
- extraction.py: orchestration of LLM extraction per-use-case
- rules_engine.py: convert extraction -> TestRows, expand and dedupe
- generator.py: template-aware CSV generation
- orchestrator.py: main run_for_jira and run_for_maintenance flows
- ui_streamlit.py: Streamlit UI
- prompts.py: per-use-case prompts (drafts)
- audit.py: write audit artifacts
- utils/: helpers (json parsing, normalizers)

## Interfaces (examples)
- JiraConnector.fetch_issue(jira_id) -> JiraContext
- PortkeyVirtualClient.extract(text, classification, prompt_override) -> dict
- SnowflakeConnector.batch_get_expected_rates(queries) -> Dict[key, rate]
- generator.generate_bci_from_template(template_path, testrows) -> bytes

