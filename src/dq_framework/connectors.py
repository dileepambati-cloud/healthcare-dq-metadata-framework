"""
Source connectors (Snowflake and Oracle).

Both drivers are optional - each package is only imported when a dataset
of that source_type is actually run, so local CSV runs need neither.

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
SNOWFLAKE_REQUIRED = ("account", "user", "password", "warehouse")

ORACLE_ENV = {
    "user": "ORACLE_USER",
    "password": "ORACLE_PASSWORD",
    "dsn": "ORACLE_DSN",            # host:port/service_name
}
ORACLE_REQUIRED = ("user", "password", "dsn")


def _settings(env_map, required, label):
    settings = {k: os.getenv(v) for k, v in env_map.items()}
    missing = [env_map[k] for k in required if not settings[k]]
    if missing:
        raise EnvironmentError(f"missing {label} settings: {', '.join(missing)}")
    return {k: v for k, v in settings.items() if v}


def snowflake_settings():
    return _settings(SNOWFLAKE_ENV, SNOWFLAKE_REQUIRED, "Snowflake")


def oracle_settings():
    return _settings(ORACLE_ENV, ORACLE_REQUIRED, "Oracle")


def get_snowflake_connection():
    try:
        import snowflake.connector
    except ImportError as exc:
        raise ImportError(
            "snowflake-connector-python is not installed - pip install snowflake-connector-python"
        ) from exc
    return snowflake.connector.connect(**snowflake_settings())


def get_oracle_connection():
    try:
        import oracledb   # thin mode, no Oracle client install needed
    except ImportError as exc:
        raise ImportError("oracledb is not installed - pip install oracledb") from exc
    return oracledb.connect(**oracle_settings())


def _safe_identifier(name):
    # source_location comes from config; only allow DB.SCHEMA.TABLE style names
    parts = name.split(".")
    if not 1 <= len(parts) <= 3 or not all(p.replace("_", "").replace("$", "").isalnum() for p in parts):
        raise ValueError(f"invalid table name in config: {name!r}")
    return name


def _query_to_frame(conn, sql):
    cur = conn.cursor()
    try:
        cur.execute(sql)
        cols = [c[0].lower() for c in cur.description]
        rows = cur.fetchall()
    finally:
        if hasattr(cur, "close"):
            cur.close()
    # text everywhere + blanks for NULL, same shape as the CSV loader
    return pd.DataFrame(rows, columns=cols).fillna("").astype(str)


def _read(table_name, limit, conn, connect_fn, limit_sql):
    sql = f"SELECT * FROM {_safe_identifier(table_name)}"
    if limit:
        sql += limit_sql.format(n=int(limit))

    own_conn = conn is None
    conn = conn or connect_fn()
    try:
        return _query_to_frame(conn, sql)
    finally:
        if own_conn:
            conn.close()


def read_table(table_name, limit=None, conn=None):
    """Read a Snowflake table (DB.SCHEMA.TABLE) into a DataFrame."""
    return _read(table_name, limit, conn, get_snowflake_connection, " LIMIT {n}")


def read_oracle_table(table_name, limit=None, conn=None):
    """Read an Oracle table (SCHEMA.TABLE) into a DataFrame."""
    # Oracle 12c+ syntax; older versions would need ROWNUM
    return _read(table_name, limit, conn, get_oracle_connection, " FETCH FIRST {n} ROWS ONLY")


# source_type in dq_dataset_config -> reader
READERS = {
    "table": read_table,          # kept for configs written before 'snowflake' existed
    "snowflake": read_table,
    "oracle": read_oracle_table,
}
