"""
Source connectors.

Snowflake is optional - the package is only imported when a dataset with
source_type = 'table' is actually run, so local CSV runs don't need it.

Connection settings come from environment variables (see .env.example).
Never put credentials in the config tables or in code.
"""
import os

import pandas as pd

SNOWFLAKE_ENV = {
    "account": "SNOWFLAKE_ACCOUNT",
    "user": "SNOWFLAKE_USER",
    "password": "SNOWFLAKE_PASSWORD",
    "warehouse": "SNOWFLAKE_WAREHOUSE",
    "database": "SNOWFLAKE_DATABASE",
    "schema": "SNOWFLAKE_SCHEMA",
    "role": "SNOWFLAKE_ROLE",
}
REQUIRED = ("account", "user", "password", "warehouse")


def snowflake_settings():
    settings = {k: os.getenv(v) for k, v in SNOWFLAKE_ENV.items()}
    missing = [SNOWFLAKE_ENV[k] for k in REQUIRED if not settings[k]]
    if missing:
        raise EnvironmentError(f"missing Snowflake settings: {', '.join(missing)}")
    return {k: v for k, v in settings.items() if v}


def get_snowflake_connection():
    try:
        import snowflake.connector
    except ImportError as exc:
        raise ImportError(
            "snowflake-connector-python is not installed - pip install snowflake-connector-python"
        ) from exc
    return snowflake.connector.connect(**snowflake_settings())


def _safe_identifier(name):
    # source_location comes from config; only allow DB.SCHEMA.TABLE style names
    parts = name.split(".")
    if not 1 <= len(parts) <= 3 or not all(p.replace("_", "").isalnum() for p in parts):
        raise ValueError(f"invalid table name in config: {name!r}")
    return name


def read_table(table_name, limit=None, conn=None):
    """Read a Snowflake table into a DataFrame (all columns as text, like the CSV path)."""
    sql = f"SELECT * FROM {_safe_identifier(table_name)}"
    if limit:
        sql += f" LIMIT {int(limit)}"

    own_conn = conn is None
    conn = conn or get_snowflake_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [c[0].lower() for c in cur.description]
        df = pd.DataFrame(cur.fetchall(), columns=cols)
    finally:
        if own_conn:
            conn.close()

    return df.fillna("").astype(str)
