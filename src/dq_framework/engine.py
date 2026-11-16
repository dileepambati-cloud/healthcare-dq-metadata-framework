"""
DQ engine - reads datasets + rules from metadata, runs each rule,
and writes one result row per rule into dq_result_log.
"""
import logging
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd

from .metadata import ROOT, get_active_datasets, get_active_rules
from .rules import get_rule

log = logging.getLogger(__name__)


def load_dataset(ds):
    if ds["source_type"] == "csv":
        path = Path(ds["source_location"])
        if not path.is_absolute():
            path = ROOT / path
        # read everything as string first - type issues are DQ findings, not crashes
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    raise NotImplementedError(f"source_type {ds['source_type']} not supported yet")


def evaluate_rule(df, rule, context):
    fn = get_rule(rule["rule_type"])
    failed_mask = fn(df, rule["column_name"], rule["rule_params"], context)
    total = len(failed_mask)
    failed = int(failed_mask.sum())
    pass_pct = round(100.0 * (total - failed) / total, 2) if total else 0.0
    status = "PASS" if pass_pct >= float(rule["threshold_pct"]) else "FAIL"
    return total, failed, pass_pct, status


def run(conn, run_id=None):
    run_id = run_id or f"RUN_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"
    start = datetime.now()
    datasets = get_active_datasets(conn)

    # load all datasets up front so referential rules can see each other
    context = {ds["dataset_name"]: load_dataset(ds) for ds in datasets}

    results = []
    for ds in datasets:
        df = context[ds["dataset_name"]]
        for rule in get_active_rules(conn, ds["dataset_id"]):
            try:
                total, failed, pass_pct, status = evaluate_rule(df, rule, context)
                msg = f"{failed} of {total} records failed"
            except Exception as exc:  # a broken rule shouldn't stop the whole run
                log.exception("rule %s errored", rule["rule_id"])
                total, failed, pass_pct, status, msg = len(df), None, None, "ERROR", str(exc)[:1000]

            results.append({
                "run_id": run_id,
                "rule_id": rule["rule_id"],
                "dataset_name": ds["dataset_name"],
                "rule_name": rule["rule_name"],
                "column_name": rule["column_name"],
                "total_records": total,
                "failed_records": failed,
                "pass_pct": pass_pct,
                "status": status,
                "severity": rule["severity"],
                "message": msg,
                "checked_ts": datetime.now().isoformat(timespec="seconds"),
            })

    _write_results(conn, results)
    failed_rules = sum(1 for r in results if r["status"] != "PASS")
    high_fail = any(r["status"] != "PASS" and r["severity"] == "HIGH" for r in results)
    run_status = "FAILED" if high_fail else ("WARN" if failed_rules else "SUCCESS")

    conn.execute(
        "INSERT INTO dq_run_log VALUES (?,?,?,?,?,?,?)",
        (run_id, start.isoformat(timespec="seconds"), datetime.now().isoformat(timespec="seconds"),
         len(datasets), len(results), failed_rules, run_status),
    )
    conn.commit()
    return run_id, run_status, results


def _write_results(conn, results):
    if not results:
        return
    cols = list(results[0].keys())
    sql = f"INSERT INTO dq_result_log ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})"
    conn.executemany(sql, [tuple(r[c] for c in cols) for r in results])
