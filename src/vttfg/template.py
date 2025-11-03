import pandas as pd, os, logging
from vttfg.config import CONFIG
logger = logging.getLogger("vttfg.template")

def read_template_metadata(path=None):
    path = path or CONFIG.bci_template_path
    if not os.path.exists(path):
        raise RuntimeError(f"Template file not found: {path}")
    try:
        df = pd.read_csv(path, dtype=str).fillna("")
    except Exception:
        df = pd.read_excel(path, dtype=str).fillna("")
    cols = list(df.columns)
    lc = {c.lower(): c for c in cols}
    def pick(*names):
        for n in names:
            k = n.lower()
            if k in lc:
                return lc[k]
        return None
    item_col = pick("product code","product_code","product class code","product class")
    name_col = pick("product name","description","product description","product_class_name")
    division_col = pick("division code","division")
    dept_col = pick("department code","department")
    company_col = pick("company code","company")
    product_list = set()
    product_name_to_codes = {}
    product_to_division = {}
    product_to_department = {}
    product_to_company = {}
    if item_col:
        for _, r in df.iterrows():
            code = str(r.get(item_col,"")).strip()
            if not code:
                continue
            codeu = code.upper()
            product_list.add(codeu)
            if name_col:
                name = str(r.get(name_col,"")).strip().lower()
                if name:
                    product_name_to_codes.setdefault(name, set()).add(codeu)
            product_to_division[codeu] = str(r.get(division_col,"")) if division_col else ""
            product_to_department[codeu] = str(r.get(dept_col,"")) if dept_col else ""
            product_to_company[codeu] = str(r.get(company_col,"")) if company_col else ""
    meta = {
        "columns": cols,
        "product_list": product_list,
        "product_name_to_codes": product_name_to_codes,
        "product_to_division": product_to_division,
        "product_to_department": product_to_department,
        "product_to_company": product_to_company,
        "df": df
    }
    logger.info("Loaded template metadata: %d products", len(product_list))
    return meta

def resolve_products(extracted_list, template_meta):
    from vttfg.config import CONFIG
    resolved = []
    notes = []
    product_list = template_meta.get("product_list", set())
    name_map = template_meta.get("product_name_to_codes", {})
    for x in extracted_list or []:
        if not x: continue
        xu = x.strip().upper()
        if xu in product_list:
            resolved.append(xu); notes.append(f"Exact code match: {xu}"); continue
        nx = x.strip().lower()
        if nx in name_map:
            codes = sorted(list(name_map[nx]))
            resolved.extend(codes); notes.append(f"Name match for {x} -> {codes}"); continue
        matches = []
        for name, codes in name_map.items():
            if nx in name or name in nx:
                matches.extend(list(codes))
        if matches:
            matches = list(dict.fromkeys(matches))
            resolved.extend(matches); notes.append(f"Substring matches for {x} -> {matches}"); continue
        resolved.append(CONFIG.default_item.upper()); notes.append(f"No match for {x}, using default {CONFIG.default_item}")
    # dedupe preserving order
    out = []
    seen = set()
    for c in resolved:
        if c not in seen:
            out.append(c); seen.add(c)
    return out, notes
