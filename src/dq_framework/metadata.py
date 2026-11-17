"""
Metadata store: creates the config/log tables and reads active rules.

Locally this uses SQLite so the project runs with zero setup.
The same DDL is used for Snowflake (see sql/ddl).
"""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DDL_DIR = ROOT / "sql" / "ddl"
SEED_DIR = ROOT / "sql" / "seed"


def get_connection(db_path=":memory:"):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _run_sql_dir(conn, folder):
    # files are numbered (01_, 02_ ...) so sorted order = run order
    for path in sorted(folder.glob("*.sql")):
        conn.executescript(path.read_text())


def init_metadata(conn, seed=True):
    _run_sql_dir(conn, DDL_DIR)
    if seed:
        already = conn.execute("SELECT COUNT(*) FROM dq_rule_config").fetchone()[0]
        if already == 0:
            _run_sql_dir(conn, SEED_DIR)
    conn.commit()


def get_active_datasets(conn):
    rows = conn.execute(
        "SELECT * FROM dq_dataset_config WHERE is_active = 'Y' ORDER BY dataset_id"
    ).fetchall()
    return [dict(r) for r in rows]


def get_active_rules(conn, dataset_id):
    rows = conn.execute(
        """SELECT * FROM dq_rule_config
           WHERE dataset_id = ? AND is_active = 'Y'
           ORDER BY rule_id""",
        (dataset_id,),
    ).fetchall()
    rules = []
    for r in rows:
        rule = dict(r)
        rule["rule_params"] = json.loads(rule["rule_params"] or "{}")
        rules.append(rule)
    return rules
