from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class JiraContext:
    jira_id: str
    title: str = ""
    description: str = ""
    comments: List[str] = field(default_factory=list)
    linked_docs: List[str] = field(default_factory=list)
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    raw_payload: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExtractionResult:
    item_codes: List[str] = field(default_factory=list)
    product_classes: List[str] = field(default_factory=list)
    states: List[str] = field(default_factory=list)
    postal_codes: List[str] = field(default_factory=list)
    date_specs: List[Dict[str, Any]] = field(default_factory=list)
    flex_fields: Dict[str, Any] = field(default_factory=dict)
    taxability_matrix: List[Dict[str, Any]] = field(default_factory=list)
    category_mapping: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    raw_extracted_text: str = ""

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: v for k, v in d.items() if k in cls.__annotations__})

@dataclass
class TestRow:
    document_number: int
    transaction_type: str
    message_type: str
    company_code: str
    division_code: str
    department_code: str
    line_item_number: int
    extended_price: str
    flex1: str
    flex2: str
    flex3: str
    flex4: str
    flex5: str
    document_date: str
    dest_country: str
    dest_main_division: str
    dest_postal_code: str
    phys_country: str
    phys_main_division: str
    phys_postal_code: str
    product_class_code: str
    product_code: str
    expected_value: Optional[str] = None
    source: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
