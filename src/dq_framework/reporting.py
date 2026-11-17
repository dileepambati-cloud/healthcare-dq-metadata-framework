"""
HTML summary report for a single run.

Plain HTML + inline CSS so it opens anywhere and can be attached to an
email or dropped on a shared drive without extra files.
"""
from datetime import datetime
from html import escape
from pathlib import Path

STATUS_COLORS = {
    "PASS": "#1e7e34",
    "FAIL": "#c82333",
    "ERROR": "#856404",
}
RUN_COLORS = {"SUCCESS": "#1e7e34", "WARN": "#d39e00", "FAILED": "#c82333"}

CSS = """
body { font-family: Arial, Helvetica, sans-serif; margin: 24px; color: #222; }
h1 { font-size: 20px; margin-bottom: 4px; }
.meta { color: #666; font-size: 13px; margin-bottom: 16px; }
.cards { display: flex; gap: 12px; margin-bottom: 20px; }
.card { border: 1px solid #ddd; border-radius: 6px; padding: 10px 16px; min-width: 110px; }
.card .num { font-size: 22px; font-weight: bold; }
.card .lbl { font-size: 12px; color: #666; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th, td { border: 1px solid #ddd; padding: 6px 8px; text-align: left; }
th { background: #f4f4f4; }
tr.fail { background: #fff5f5; }
.badge { color: #fff; padding: 2px 8px; border-radius: 10px; font-size: 12px; }
"""


def _badge(text, colors):
    color = colors.get(text, "#6c757d")
    return f'<span class="badge" style="background:{color}">{escape(str(text))}</span>'


def summarize(results):
    total = len(results)
    failed = sum(1 for r in results if r["status"] != "PASS")
    high = sum(1 for r in results if r["status"] != "PASS" and r["severity"] == "HIGH")
    datasets = len({r["dataset_name"] for r in results})
    return {"total": total, "passed": total - failed, "failed": failed,
            "high_failed": high, "datasets": datasets}


def build_html(run_id, run_status, results):
    s = summarize(results)
    # failures first, then by dataset so the problems are at the top
    ordered = sorted(results, key=lambda r: (r["status"] == "PASS", r["dataset_name"], r["rule_id"]))

    rows = []
    for r in ordered:
        cls = "" if r["status"] == "PASS" else ' class="fail"'
        rows.append(
            f"<tr{cls}>"
            f"<td>{escape(str(r['dataset_name']))}</td>"
            f"<td>{escape(str(r['rule_name']))}</td>"
            f"<td>{escape(str(r['column_name'] or '-'))}</td>"
            f"<td>{escape(str(r['severity']))}</td>"
            f"<td>{r['failed_records'] if r['failed_records'] is not None else '-'}</td>"
            f"<td>{r['pass_pct'] if r['pass_pct'] is not None else '-'}</td>"
            f"<td>{_badge(r['status'], STATUS_COLORS)}</td>"
            f"<td>{escape(str(r['message'] or ''))}</td>"
            "</tr>"
        )

    cards = "".join(
        f'<div class="card"><div class="num">{v}</div><div class="lbl">{k}</div></div>'
        for k, v in [("Datasets", s["datasets"]), ("Checks", s["total"]), ("Passed", s["passed"]),
                     ("Failed", s["failed"]), ("High severity failed", s["high_failed"])]
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>DQ report {escape(run_id)}</title>
<style>{CSS}</style></head>
<body>
<h1>Data Quality Report {_badge(run_status, RUN_COLORS)}</h1>
<div class="meta">Run {escape(run_id)} &middot; generated {datetime.now():%Y-%m-%d %H:%M}</div>
<div class="cards">{cards}</div>
<table>
<tr><th>Dataset</th><th>Rule</th><th>Column</th><th>Severity</th><th>Failed</th>
<th>Pass %</th><th>Status</th><th>Details</th></tr>
{''.join(rows)}
</table>
</body></html>
"""


def write_report(run_id, run_status, results, out_dir="output"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"dq_report_{run_id}.html"
    path.write_text(build_html(run_id, run_status, results), encoding="utf-8")
    return path
