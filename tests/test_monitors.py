import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dq_framework import monitors  # noqa: E402
from dq_framework.metadata import get_connection, init_metadata  # noqa: E402


@pytest.fixture
def conn():
    c = get_connection()
    init_metadata(c, seed=False)
    return c


def ctx(conn, run_id, name="claims"):
    return {"_meta": {"conn": conn, "run_id": run_id, "dataset_name": name}}


# ---------------- freshness
def test_freshness_pass_and_fail():
    recent = (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    old = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    df = pd.DataFrame({"loaded_at": [old, recent]})
    mask, _ = monitors.freshness(df, "loaded_at", {"max_age_hours": 24})
    assert not mask.iloc[0]

    stale = pd.DataFrame({"loaded_at": [old]})
    mask, msg = monitors.freshness(stale, "loaded_at", {"max_age_hours": 24})
    assert mask.iloc[0]
    assert "limit=24h" in msg


def test_freshness_no_valid_dates():
    mask, msg = monitors.freshness(pd.DataFrame({"d": ["", "x"]}), "d", {})
    assert mask.iloc[0] and "no valid" in msg


# ---------------- volume
def test_volume_first_run_records_history(conn):
    df = pd.DataFrame({"a": range(100)})
    mask, msg = monitors.volume_anomaly(df, None, {}, ctx(conn, "r1"))
    assert not mask.iloc[0] and "no history" in msg
    assert conn.execute("SELECT COUNT(*) FROM dq_volume_history").fetchone()[0] == 1


def test_volume_flags_big_drop(conn):
    for i in range(3):
        monitors.volume_anomaly(pd.DataFrame({"a": range(100)}), None, {}, ctx(conn, f"r{i}"))
    mask, msg = monitors.volume_anomaly(pd.DataFrame({"a": range(40)}), None,
                                        {"tolerance_pct": 30}, ctx(conn, "r9"))
    assert mask.iloc[0]
    assert "change=60.0%" in msg


def test_volume_within_tolerance(conn):
    monitors.volume_anomaly(pd.DataFrame({"a": range(100)}), None, {}, ctx(conn, "r1"))
    mask, _ = monitors.volume_anomaly(pd.DataFrame({"a": range(110)}), None,
                                      {"tolerance_pct": 30}, ctx(conn, "r2"))
    assert not mask.iloc[0]


# ---------------- schema drift
def test_infer_type():
    assert monitors.infer_type(pd.Series(["1", "2", ""])) == "integer"
    assert monitors.infer_type(pd.Series(["1.5", "2"])) == "decimal"
    assert monitors.infer_type(pd.Series(["2026-01-01", "2025-12-31"])) == "date"
    assert monitors.infer_type(pd.Series(["abc", "1"])) == "string"


def test_schema_baseline_then_drift(conn):
    base = pd.DataFrame({"id": ["1", "2"], "amt": ["1.5", "2.0"], "name": ["a", "b"]})
    mask, msg = monitors.schema_drift(base, None, {}, ctx(conn, "r1"))
    assert not mask.iloc[0] and "baseline captured" in msg

    mask, msg = monitors.schema_drift(base, None, {}, ctx(conn, "r2"))
    assert not mask.iloc[0]

    changed = pd.DataFrame({"id": ["1", "x"], "amt": ["1.5", "2.0"], "email": ["a@x.com", "b@x.com"]})
    mask, msg = monitors.schema_drift(changed, None, {}, ctx(conn, "r3"))
    assert mask.iloc[0]
    assert "added=['email']" in msg
    assert "removed=['name']" in msg
    assert "id:integer->string" in msg


def test_monitor_without_context_errors():
    with pytest.raises(ValueError):
        monitors.volume_anomaly(pd.DataFrame({"a": [1]}), None, {}, None)
