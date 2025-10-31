# VTTFG - High Level Architecture

This document describes the high-level architecture of the Vertex Tax Test File Generator (VTTFG).

## Overview
VTTFG converts tax-rule change requests (JIRA tickets and linked Google Docs/Sheets) into Vertex BCI CSV files.
Core components:
- Streamlit UI (human-in-loop)
- Orchestrator (workflow coordinator)
- Connectors (Jira, Google Docs/Sheets, Snowflake, GeoNames, Filestore, LLM client)
- LLM Processor (Portkey virtual key)
- Rules Engine (resolves product/division and expands combinations)
- Generator (maps TestRows into BCI template)
- Audit & Logging

See docs/WORKFLOW.md and docs/ARCHITECTURE_LOW_LEVEL.md for more details.
