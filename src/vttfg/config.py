from dataclasses import dataclass
from dotenv import load_dotenv
import os
load_dotenv()
@dataclass
class Config:
    portkey_virtual_key: str = os.getenv('PORTKEY_VIRTUAL_KEY','')
    portkey_base_url: str = os.getenv('PORTKEY_BASE_URL','http://cybertron-service-gateway.service.prod.ddsd:8080/v1')
    portkey_model: str = os.getenv('PORTKEY_MODEL','gpt-4o-mini')
    jira_base_url: str = os.getenv('JIRA_BASE_URL','')
    jira_user: str = os.getenv('JIRA_USER','')
    jira_api_token: str = os.getenv('JIRA_API_TOKEN','')
    google_service_account_file: str = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE','')
    sf_account: str = os.getenv('SNOWFLAKE_ACCOUNT','')
    sf_user: str = os.getenv('SNOWFLAKE_USER','')
    sf_password: str = os.getenv('SNOWFLAKE_PASSWORD','')
    bci_template_path: str = os.getenv('BCI_TEMPLATE_PATH','./data/BCI_Input_Template_US_and_Canada.csv')
    output_dir: str = os.getenv('VTTFG_OUTPUT_DIR','./output')
    default_item: str = os.getenv('DEFAULT_ITEM','BWATER')
    default_extended_price: float = float(os.getenv('DEFAULT_EXT_PRICE','9.99'))
    max_combinations: int = int(os.getenv('MAX_COMBINATIONS','2000'))
    llm_conf_threshold: float = float(os.getenv('LLM_CONF_THRESHOLD','0.7'))
CONFIG = Config()
