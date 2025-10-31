import os, json, datetime, logging
from .config import CONFIG
logger = logging.getLogger('vttfg.audit')
def write_audit(run_id: str, rows: list, metadata: dict):
    out_dir = CONFIG.output_dir
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"audit_{run_id}.json")
    payload = {'run_id': run_id, 'rows_count': len(rows), 'metadata': metadata, 'generated_at': datetime.datetime.utcnow().isoformat()}
    with open(path, 'w') as f:
        json.dump(payload, f, indent=2)
    logger.info("Wrote audit %s", path, extra={"run_id":run_id,"step":"audit_write"})
    return path
