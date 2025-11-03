import logging
from ..config import CONFIG
logger = logging.getLogger("vttfg.snowflake")
try:
    import snowflake.connector as sf
except Exception:
    sf = None

class SnowflakeConnector:
    def __init__(self):
        if not sf:
            raise RuntimeError("snowflake-connector-python not installed")
        if not (CONFIG.snowflake_account and CONFIG.snowflake_user and CONFIG.snowflake_password):
            raise RuntimeError("Snowflake credentials not configured in .env")
        self.conn = sf.connect(
            user=CONFIG.snowflake_user,
            password=CONFIG.snowflake_password,
            account=CONFIG.snowflake_account,
            warehouse=CONFIG.snowflake_warehouse or None,
            database=CONFIG.snowflake_database or None,
            schema=CONFIG.snowflake_schema or None,
            role=CONFIG.snowflake_role or None
        )

    def batch_get_expected_rates(self, queries):
        """
        queries: list of tuples (product_code, state, postal, date)
        returns dict mapping key->rate
        """
        out = {}
        cur = self.conn.cursor()
        try:
            for (prod, state, postal, date) in queries:
                sql = "SELECT rate FROM TAX_RATES WHERE product_code=%s AND state=%s AND postal=%s AND effective_date <= %s ORDER BY effective_date DESC LIMIT 1"
                cur.execute(sql, (prod, state or "", postal or "", date or "1970-01-01"))
                row = cur.fetchone()
                if row:
                    out[(prod.upper(), (state or "").upper(), (postal or ""), date)] = row[0]
        finally:
            cur.close()
        return out
