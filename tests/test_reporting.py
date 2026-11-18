import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dq_framework import reporting  # noqa: E402

RESULTS = [
    {"rule_id": 1, "dataset_name": "claims", "rule_name": "claim_id_unique", "column_name": "claim_id",
     "severity": "HIGH", "failed_records": 2, "pass_pct": 98.3, "status": "FAIL",
     "message": "2 of 120 records failed"},
    {"rule_id": 2, "dataset_name": "claims", "rule_name": "claims_freshness", "column_name": None,
     "severity": "HIGH", "failed_records": 0, "pass_pct": 100.0, "status": "PASS", "message": "ok"},
    {"rule_id": 3, "dataset_name": "members", "rule_name": "zip_format", "column_name": "zip_code",
     "severity": "LOW", "failed_records": None, "pass_pct": None, "status": "ERROR",
     "message": "<bad> & broken"},
]


def test_summary_counts():
    s = reporting.summarize(RESULTS)
    assert s == {"total": 3, "passed": 1, "failed": 2, "high_failed": 1, "datasets": 2}


def test_html_has_failures_first_and_escapes():
    html = reporting.build_html("RUN_1", "FAILED", RESULTS)
    assert html.index("claim_id_unique") < html.index("claims_freshness")
    assert "&lt;bad&gt; &amp; broken" in html
    assert "<bad>" not in html


def test_write_report(tmp_path):
    path = reporting.write_report("RUN_1", "FAILED", RESULTS, out_dir=tmp_path)
    assert path.exists() and path.name == "dq_report_RUN_1.html"
