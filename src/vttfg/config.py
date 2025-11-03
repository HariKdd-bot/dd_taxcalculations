import os
from dotenv import load_dotenv
from dataclasses import dataclass

load_dotenv()

@dataclass
class Config:
    portkey_virtual_key: str = os.getenv("PORTKEY_VIRTUAL_KEY")
    portkey_base_url: str = os.getenv("PORTKEY_BASE_URL")
    portkey_model: str = os.getenv("PORTKEY_MODEL", "gpt-4o-mini")

    jira_base_url: str = os.getenv("JIRA_BASE_URL")
    jira_user: str = os.getenv("JIRA_USER")
    jira_api_token: str = os.getenv("JIRA_API_TOKEN")

    google_credentials: str = os.getenv("GOOGLE_CREDENTIALS_JSON")

    snowflake_account: str = os.getenv("SNOWFLAKE_ACCOUNT")
    snowflake_user: str = os.getenv("SNOWFLAKE_USER")
    snowflake_password: str = os.getenv("SNOWFLAKE_PASSWORD")
    snowflake_role: str = os.getenv("SNOWFLAKE_ROLE")
    snowflake_warehouse: str = os.getenv("SNOWFLAKE_WAREHOUSE")
    snowflake_database: str = os.getenv("SNOWFLAKE_DATABASE")
    snowflake_schema: str = os.getenv("SNOWFLAKE_SCHEMA")

    bci_template_path: str = os.getenv("BCI_TEMPLATE_PATH", "sample_inputs/BCI Input Template_US and Canada - BCI Input Template_US and Canada.csv")
    output_dir: str = os.getenv("OUTPUT_DIR", "output")
    default_item: str = os.getenv("DEFAULT_ITEM", "BWATER")
    default_extended_price: str = os.getenv("DEFAULT_EXTENDED_PRICE", "")
    llm_confidence_threshold: float = float(os.getenv("LLM_CONFIDENCE_THRESHOLD", 0.6))
    data_dir: str = os.getenv("DATA_DIR", "data")

CONFIG = Config()
