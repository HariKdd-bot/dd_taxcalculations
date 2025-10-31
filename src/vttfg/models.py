from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, date
@dataclass
class JiraContext:
    jira_id: str
    title: str
    description: str
    comments: List[str]
    linked_docs: List[str]
    attachments: List[Dict[str,Any]]
    created_at: datetime
    raw_payload: Dict[str,Any] = field(default_factory=dict)
@dataclass
class ExtractionResult:
    classification: str
    item_codes: List[str]
    product_classes: List[str]
    division_codes: List[str]
    department_codes: List[str]
    postal_codes: List[str]
    states: List[str]
    date_specs: List[Dict[str,str]]
    taxability_matrix: Optional[Dict[str,Any]]
    category_mapping: Optional[Dict[str,Any]]
    flex_fields: Dict[str,Any]
    confidence: float
    raw_llm_response: str
@dataclass
class TestRow:
    transaction_type: str
    item_code: str
    product_class: Optional[str]
    document_date: date
    dest_postal_code: Optional[str]
    dest_state: Optional[str]
    extended_price: float
    flex_field_2: Optional[str]
    flex_field_3: Optional[str]
    division_code: Optional[str]
    department_code: Optional[str]
    company_code: Optional[str]
    expected_tax_rate: Optional[float]
    source: Dict[str,Any]
    metadata: Dict[str,Any] = field(default_factory=dict)
