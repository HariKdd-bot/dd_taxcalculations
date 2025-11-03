import logging
from vttfg.template import read_template_metadata, resolve_products
from vttfg.geoutils import postal_to_state_country, representative_zip_for_state
from vttfg.models import TestRow
from vttfg.config import CONFIG
logger = logging.getLogger("vttfg.rules")

def build_testrows(extraction, template_path=None):
    template_meta = read_template_metadata(template_path)
    items = extraction.get("item_codes") or extraction.get("product_classes") or []
    resolved, notes = resolve_products(items, template_meta)
    ds = extraction.get("date_specs") or []
    doc_date = None
    for d in ds:
        if d.get("type") == "effective" and d.get("date"):
            doc_date = d.get("date"); break
    if not doc_date:
        doc_date = extraction.get("jira_created_at") or ""
    states = extraction.get("states") or []
    postals = extraction.get("postal_codes") or []
    destinations = []
    if postals:
        for p in postals:
            st, country = postal_to_state_country(p)
            destinations.append({"dest_country": country or "", "dest_main_division": st or "", "dest_postal_code": p})
    elif states:
        for s in states:
            z = representative_zip_for_state(s)
            destinations.append({"dest_country": "US", "dest_main_division": s, "dest_postal_code": z or ""})
    else:
        destinations.append({"dest_country": "", "dest_main_division": "", "dest_postal_code": ""})

    rows = []
    doc_num = 1
    for prod in resolved:
        div = template_meta.get("product_to_division", {}).get(prod,"")
        dept = template_meta.get("product_to_department", {}).get(prod,"")
        comp = template_meta.get("product_to_company", {}).get(prod,"")
        for dest in destinations:
            tr = TestRow(
                document_number=doc_num,
                transaction_type="SALE",
                message_type="INVOICE",
                company_code=comp,
                division_code=div,
                department_code=dept,
                line_item_number=1,
                extended_price="",
                flex1=extraction.get("flex_fields",{}).get("flex_field_1",""),
                flex2=extraction.get("flex_fields",{}).get("flex_field_2",""),
                flex3=extraction.get("flex_fields",{}).get("flex_field_3",""),
                flex4=extraction.get("flex_fields",{}).get("flex_field_4",""),
                flex5=extraction.get("flex_fields",{}).get("flex_field_5",""),
                document_date=doc_date,
                dest_country=dest.get("dest_country",""),
                dest_main_division=dest.get("dest_main_division",""),
                dest_postal_code=dest.get("dest_postal_code",""),
                phys_country=dest.get("dest_country",""),
                phys_main_division=dest.get("dest_main_division",""),
                phys_postal_code=dest.get("dest_postal_code",""),
                product_class_code="",
                product_code=prod,
                expected_value="",
                source={"mapping_notes": notes},
                metadata={"confidence": extraction.get("confidence",0.0)}
            )
            rows.append(tr)
            doc_num += 1
    return rows
