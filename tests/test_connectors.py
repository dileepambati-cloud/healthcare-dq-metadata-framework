import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dq_framework import connectors  # noqa: E402


class FakeCursor:
    description = [("MEMBER_ID",), ("PLAN_CODE",)]

    def execute(self, sql):
        self.sql = sql

    def fetchall(self):
        return [("M00001", "PPO"), ("M00002", None)]


class FakeConn:
    def __init__(self):
        self.cur = FakeCursor()
        self.closed = False

    def cursor(self):
        return self.cur

    def close(self):
        self.closed = True


def test_read_table_with_given_connection():
    conn = FakeConn()
    df = connectors.read_table("DQ_DEMO.PUBLIC.MEMBERS", limit=5, conn=conn)
    assert list(df.columns) == ["member_id", "plan_code"]
    assert df.loc[1, "plan_code"] == ""          # NULL comes back as blank like the CSV path
    assert conn.cur.sql.endswith("LIMIT 5")
    assert not conn.closed                         # caller owns the connection


@pytest.mark.parametrize("bad", ["members; DROP TABLE x", "a.b.c.d", "db.schema.tab le", ""])
def test_rejects_bad_table_names(bad):
    with pytest.raises(ValueError):
        connectors.read_table(bad, conn=FakeConn())


def test_missing_settings(monkeypatch):
    for var in connectors.SNOWFLAKE_ENV.values():
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(EnvironmentError) as err:
        connectors.snowflake_settings()
    assert "SNOWFLAKE_ACCOUNT" in str(err.value)


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "acct")
    monkeypatch.setenv("SNOWFLAKE_USER", "u")
    monkeypatch.setenv("SNOWFLAKE_PASSWORD", "p")
    monkeypatch.setenv("SNOWFLAKE_WAREHOUSE", "wh")
    monkeypatch.delenv("SNOWFLAKE_ROLE", raising=False)
    s = connectors.snowflake_settings()
    assert s["account"] == "acct" and "role" not in s


# ---------------- Oracle
def test_read_oracle_table_uses_fetch_first():
    conn = FakeConn()
    df = connectors.read_oracle_table("CLAIMS_OWNER.CLAIMS", limit=10, conn=conn)
    assert conn.cur.sql == "SELECT * FROM CLAIMS_OWNER.CLAIMS FETCH FIRST 10 ROWS ONLY"
    assert len(df) == 2


def test_oracle_missing_settings(monkeypatch):
    for var in connectors.ORACLE_ENV.values():
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(EnvironmentError) as err:
        connectors.oracle_settings()
    assert "ORACLE_DSN" in str(err.value)


def test_readers_registry():
    assert connectors.READERS["oracle"] is connectors.read_oracle_table
    assert connectors.READERS["snowflake"] is connectors.read_table
