from typing import List, Dict
from vttfg.models import ExtractionResult, TestRow
from vttfg.config import CONFIG
from datetime import datetime
from vttfg.connectors import geonames
import logging
logger = logging.getLogger('vttfg.rules')
def apply_rules(extr: ExtractionResult, division_map: Dict[str,str]=None) -> List[TestRow]:
    logger.info("apply_rules start: products=%d states=%d", len(extr.item_codes or []), len(extr.states or []), extra={"run_id":"-","step":"rules_start"})
    rows = []
    if division_map is None:
        division_map = {}
    for product in (extr.item_codes or [CONFIG.default_item]):
        divisions = extr.division_codes or []
        mapped = division_map.get(product.upper())
        if mapped and mapped not in divisions:
            divisions.append(mapped)
        if not divisions:
            divisions = [None]
        destinations = []
        if extr.states:
            for s in extr.states:
                postals = geonames.postals_for_jurisdiction(s, max_results=100)
                if postals:
                    destinations.extend([{'state':s,'postal_codes':[p]} for p in postals])
                else:
                    destinations.append({'state':s,'postal_codes':[None]})
        else:
            destinations = extr.postal_codes and [{'state':'','postal_codes':extr.postal_codes}] or [{'state':'US_ALL','postal_codes':[None]}]
        for div in divisions:
            for dest in destinations:
                for postal in dest.get('postal_codes') or [None]:
                    tr = TestRow(
                        transaction_type='SALE',
                        item_code=product,
                        product_class=(extr.product_classes[0] if extr.product_classes else None),
                        document_date=(datetime.utcnow().date()),
                        dest_postal_code=postal,
                        dest_state=dest.get('state'),
                        extended_price=CONFIG.default_extended_price,
                        flex_field_2=extr.flex_fields.get('flex_field_2'),
                        flex_field_3=extr.flex_fields.get('flex_field_3'),
                        division_code=div,
                        department_code=None,
                        company_code=None,
                        expected_tax_rate=None,
                        source={},
                        metadata={'extraction_confidence': extr.confidence}
                    )
                    rows.append(tr)
    logger.info("apply_rules produced %d rows", len(rows), extra={"run_id":"-","step":"rules_done"})
    return rows
def populate_expected_rates(rows, sf_connector):
    logger.info("populate_expected_rates called for %d rows", len(rows), extra={"run_id":"-","step":"populate_rates"})
    queries = []
    for r in rows:
        queries.append((r.item_code, r.dest_state, r.dest_postal_code, r.document_date.isoformat()))
    results = sf_connector.batch_get_expected_rates(queries)
    for r in rows:
        key = (r.item_code.upper(), (r.dest_state or '').upper(), (r.dest_postal_code or ''), r.document_date.isoformat())
        r.expected_tax_rate = results.get(key)
    return rows
