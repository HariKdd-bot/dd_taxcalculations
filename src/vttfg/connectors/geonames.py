import logging
from typing import List
logger = logging.getLogger('vttfg.geonames')
def postals_for_jurisdiction(jurisdiction: str, max_results: int = 1000) -> List[str]:
    jurisdiction = (jurisdiction or '').upper()
    logger.info("postals_for_jurisdiction called for %s", jurisdiction, extra={"run_id":"-","step":"geonames_lookup"})
    if jurisdiction == 'US_ALL' or not jurisdiction:
        return []
    return ['94107','94108','94109']
