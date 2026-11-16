import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dq_framework.engine import run  # noqa: E402
from dq_framework.metadata import get_active_rules, get_connection, init_metadata  # noqa: E402


def test_seed_rules_load():
    conn = get_connection()
    init_metadata(conn)
    assert len(get_active_rules(conn, 1)) == 5
    assert len(get_active_rules(conn, 2)) == 6


def test_full_run_logs_results():
    conn = get_connection()
    init_metadata(conn)
    run_id, status, results = run(conn)

    assert len(results) == 11
    # sample data has planted errors, so HIGH rules must fail
    assert status == "FAILED"
    logged = conn.execute("SELECT COUNT(*) FROM dq_result_log WHERE run_id = ?", (run_id,)).fetchone()[0]
    assert logged == 11
    by_rule = {r["rule_name"]: r for r in results}
    assert by_rule["member_id_unique"]["failed_records"] == 2
    assert by_rule["member_exists"]["failed_records"] == 1
    assert by_rule["claims_min_row_count"]["status"] == "PASS"
