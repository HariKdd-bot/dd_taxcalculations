import pandas as pd, os, logging
from typing import List, Dict
from .models import TestRow
logger = logging.getLogger('vttfg.generator')
def read_template_metadata(path: str) -> Dict:
    logger.info("read_template_metadata called for %s", path, extra={"run_id":"-","step":"template_read"})
    if not os.path.exists(path):
        return {'columns':[], 'skeleton':{}, 'product_list':set(), 'product_to_division':{}}
    try:
        df = pd.read_csv(path, nrows=1000, dtype=str)
    except Exception:
        df = pd.read_excel(path)
    columns = list(df.columns)
    product_list = set([str(x).upper() for x in df.iloc[:,0].dropna().unique()]) if df.shape[0]>0 else set()
    product_to_division = {}
    for _, row in df.iterrows():
        try:
            prod = str(row[df.columns[0]]).upper()
            for c in df.columns:
                if 'division' in c.lower():
                    product_to_division[prod] = str(row[c])
                    break
        except Exception:
            continue
    skeleton = {c:'' for c in columns}
    return {'columns':columns, 'skeleton':skeleton, 'product_list':product_list, 'product_to_division':product_to_division}
def map_testrows_to_template(testrows: List[TestRow], template_meta: Dict) -> pd.DataFrame:
    cols = template_meta.get('columns', [])
    skeleton = template_meta.get('skeleton', {})
    rows = []
    for tr in testrows:
        r = dict(skeleton)
        for c in cols:
            lc = c.lower()
            if 'item' in lc or 'product' in lc or 'sku' in lc:
                r[c] = tr.item_code
            if 'division' in lc:
                r[c] = tr.division_code or ''
            if 'postal' in lc or 'zip' in lc:
                r[c] = tr.dest_postal_code or ''
            if 'state' in lc:
                r[c] = tr.dest_state or ''
            if 'expected' in lc or 'tax' in lc:
                r[c] = tr.expected_tax_rate if tr.expected_tax_rate is not None else ''
        rows.append(r)
    df = pd.DataFrame(rows, columns=cols)
    logger.info("Mapped %d testrows to template columns", len(rows), extra={"run_id":"-","step":"map_template"})
    return df
def generate_bci_from_template(template_path: str, testrows: List[TestRow]) -> bytes:
    logger.info("generate_bci_from_template: mapping %d testrows to template %s", len(testrows), template_path, extra={"run_id":"-","step":"generate_start"})
    meta = read_template_metadata(template_path)
    df = map_testrows_to_template(testrows, meta)
    return df.to_csv(index=False).encode('utf-8')
