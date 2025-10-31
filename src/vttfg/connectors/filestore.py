import os, uuid, logging
from ..config import CONFIG
logger = logging.getLogger('vttfg.filestore')
def save_bytes(file_name: str, bytes_data: bytes) -> str:
    out_dir = CONFIG.output_dir
    os.makedirs(out_dir, exist_ok=True)
    unique = f"{uuid.uuid4().hex}_{file_name}"
    path = os.path.join(out_dir, unique)
    with open(path, 'wb') as f:
        f.write(bytes_data)
    logger.info("Saved bytes to %s (size=%d)", path, len(bytes_data), extra={"run_id":"-","step":"filestore_save"})
    return path
