"""
Dataset-level monitors: freshness, volume anomaly and schema drift.

Unlike the row-level rules in rules.py these look at the dataset as a
whole and some of them need history from earlier runs, so they read the
connection / run info the engine puts in context["_meta"].

Same signature as the other rules so the engine can treat them the same
way. They return (failed_mask, message) so the result log says *why*.
"""
from datetime import datetime

import pandas as pd


def _meta(context):
    if not context or "_meta" not in context:
        raise ValueError("monitor needs engine context (_meta) - run it through the engine")
    return context["_meta"]


# ---------------------------------------------------------------- freshness
def freshness(df, column, params, context=None):
    """Fail if the newest timestamp in `column` is older than max_age_hours."""
    max_age = float(params.get("max_age_hours", 24))
    ts = pd.to_datetime(df[column], errors="coerce", format="mixed").dropna()
    if ts.empty:
        return pd.Series([True]), f"no valid timestamps in {column}"

    newest = ts.max()
    age_hours = (pd.Timestamp(datetime.now()) - newest).total_seconds() / 3600
    failed = age_hours > max_age
    msg = f"latest {column}={newest.date()} age={age_hours:.0f}h limit={max_age:.0f}h"
    return pd.Series([failed]), msg


# ------------------------------------------------------------ volume anomaly
def volume_anomaly(df, column, params, context=None):
    """
    Compare today's row count to the average of the last N runs.
    First run(s) have no history so they just record the count and pass.
    """
    meta = _meta(context)
    conn, dataset, run_id = meta["conn"], meta["dataset_name"], meta["run_id"]
    lookback = int(params.get("lookback_runs", 7))
    tolerance = float(params.get("tolerance_pct", 30))
    current = len(df)

    rows = conn.execute(
        """SELECT row_count FROM dq_volume_history
           WHERE dataset_name = ? AND run_id <> ?
           ORDER BY captured_ts DESC LIMIT ?""",
        (dataset, run_id, lookback),
    ).fetchall()

    conn.execute(
        "INSERT INTO dq_volume_history VALUES (?,?,?,?)",
        (dataset, run_id, current, datetime.now().isoformat(timespec="seconds")),
    )

    if not rows:
        return pd.Series([False]), f"no history yet, recorded {current} rows as first point"

    avg = sum(r[0] for r in rows) / len(rows)
    change_pct = 0.0 if avg == 0 else abs(current - avg) / avg * 100
    failed = change_pct > tolerance
    msg = f"rows={current} avg_last_{len(rows)}={avg:.0f} change={change_pct:.1f}% limit={tolerance:.0f}%"
    return pd.Series([failed]), msg


# -------------------------------------------------------------- schema drift
def infer_type(series):
    """Rough type guess for a string column (CSV loads everything as text)."""
    values = series[series.astype(str).str.strip() != ""]
    if values.empty:
        return "string"
    if pd.to_numeric(values, errors="coerce").notna().all():
        nums = pd.to_numeric(values)
        return "integer" if (nums % 1 == 0).all() else "decimal"
    if pd.to_datetime(values, errors="coerce", format="mixed").notna().all():
        return "date"
    return "string"


def current_schema(df):
    return {col: (infer_type(df[col]), pos) for pos, col in enumerate(df.columns, start=1)}


def schema_drift(df, column, params, context=None):
    """
    Compare current columns/types to the stored baseline.
    No baseline yet -> save one and pass.
    """
    meta = _meta(context)
    conn, dataset = meta["conn"], meta["dataset_name"]
    now = datetime.now().isoformat(timespec="seconds")
    current = current_schema(df)

    baseline = {
        r[0]: r[1]
        for r in conn.execute(
            "SELECT column_name, data_type FROM dq_schema_baseline WHERE dataset_name = ?",
            (dataset,),
        ).fetchall()
    }

    if not baseline:
        conn.executemany(
            "INSERT INTO dq_schema_baseline VALUES (?,?,?,?,?)",
            [(dataset, col, t, pos, now) for col, (t, pos) in current.items()],
        )
        return pd.Series([False]), f"baseline captured ({len(current)} columns)"

    added = sorted(set(current) - set(baseline))
    removed = sorted(set(baseline) - set(current))
    retyped = sorted(
        f"{c}:{baseline[c]}->{current[c][0]}"
        for c in set(current) & set(baseline)
        if baseline[c] != current[c][0]
    )

    problems = []
    if added:
        problems.append(f"added={added}")
    if removed:
        problems.append(f"removed={removed}")
    if retyped:
        problems.append(f"type_changed={retyped}")

    if problems:
        return pd.Series([True]), "schema drift: " + "; ".join(problems)
    return pd.Series([False]), "schema matches baseline"


MONITOR_REGISTRY = {
    "freshness": freshness,
    "volume_anomaly": volume_anomaly,
    "schema_drift": schema_drift,
}
