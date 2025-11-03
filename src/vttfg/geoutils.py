import csv, os, logging
from vttfg.config import CONFIG
logger = logging.getLogger("vttfg.geoutils")

_us_cache = None
def load_us_zips(path=None):
    global _us_cache
    if _us_cache is not None:
        return _us_cache
    path = path or (os.path.join(CONFIG.data_dir, "us_sample_zips.csv"))
    if not os.path.exists(path):
        logger.warning("US zips file not found: %s", path)
        _us_cache = {}
        return _us_cache
    d = {}
    with open(path, newline="", encoding="utf-8") as fh:
        r = csv.DictReader(fh)
        for row in r:
            z = row.get("zip"); state = row.get("state")
            if z and state:
                d[z] = state
    _us_cache = d
    return d

def postal_to_state_country(postal):
    zips = load_us_zips()
    state = zips.get(str(postal))
    if state:
        return state, "US"
    return None, None

def representative_zip_for_state(state):
    zips = load_us_zips()
    for z,s in zips.items():
        if s.upper() == state.upper():
            return z
    return None
