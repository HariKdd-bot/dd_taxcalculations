# VTTFG - Workflow and Sequence

This document shows the orchestration sequence for a JIRA-driven run.

1. UI: user inputs JIRA ID and optionally selects BCI template and overrides.
2. Orchestrator.fetch_issue -> JiraContext (title, description, comments, linked docs).
3. Orchestrator filters linked docs (ignore template/result files).
4. Build context_blob from JIRA and linked doc texts.
5. LLM.classify(context_blob) -> suggested use case (UC2/UC3/UC4/UC6/Maintenance).
6. Human-in-loop: user can accept or override classification and core extracted values.
7. LLM.extract(context_blob, extraction_prompt_for_uc) -> JSON extraction result.
8. Normalization: product codes uppercased, date normalization, state codes uppercased.
9. Read template mapping (product->division/department/company).
10. Rules engine: resolve division, expand combinations (postal * division * product), enforce caps.
11. Snowflake: batch_get_expected_rates for unique combinations.
12. Generator: map TestRows to BCI template columns and produce CSV.
13. Filestore: save CSV and audit artifacts.
14. UI: present preview and download link.

See docs/ARCHITECTURE_HIGH_LEVEL.md for component responsibilities.
