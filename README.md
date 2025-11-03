# VTTFG - Vertex Tax Test File Generator (With Logging)
Generated.


project working parts


vttfg_project/
├── README.md
├── requirements.txt
├── .env.example
├── prompts/
│   ├── classify.json
│   └── uc3.json
├── data/
│   └── us_sample_zips.csv
├── sample_inputs/
│   └── (put your BCI Input Template CSV here)
└── src/
    └── vttfg/
        ├── __init__.py
        ├── config.py
        ├── logging_config.py
        ├── models.py
        ├── prompts_loader.py
        ├── llm.py
        ├── connectors/
        │   ├── __init__.py
        │   ├── jira.py
        │   ├── google_docs.py
        │   ├── google_sheets.py
        │   └── snowflake.py
        ├── template.py
        ├── geoutils.py
        ├── rules.py
        ├── generator.py
        ├── validators.py
        ├── orchestrator.py
        └── cli.py
