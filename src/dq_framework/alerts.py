"""
Email alert when HIGH severity checks fail.

If SMTP_HOST isn't set the alert is only logged (handy for local runs and
CI) - nothing breaks just because there is no mail server.
"""
import logging
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

log = logging.getLogger(__name__)


def high_failures(results):
    return [r for r in results if r["status"] != "PASS" and r["severity"] == "HIGH"]


def build_message(run_id, results, sender, recipients, report_path=None):
    failures = high_failures(results)
    msg = EmailMessage()
    msg["Subject"] = f"[DQ] {len(failures)} HIGH severity check(s) failed - {run_id}"
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)

    lines = [f"Run {run_id} has {len(failures)} HIGH severity failure(s):", ""]
    for r in failures:
        lines.append(f"- {r['dataset_name']}.{r['rule_name']}: {r['message']}")
    lines += ["", "Full results are in dq_result_log for this run_id."]
    if report_path:
        lines.append("HTML report attached.")
    msg.set_content("\n".join(lines))

    if report_path:
        p = Path(report_path)
        msg.add_attachment(p.read_bytes(), maintype="text", subtype="html", filename=p.name)
    return msg


def send_alert(run_id, results, report_path=None, smtp_cls=smtplib.SMTP):
    """Returns True if an email was sent, False if nothing to send / no SMTP configured."""
    if not high_failures(results):
        return False

    host = os.getenv("SMTP_HOST")
    sender = os.getenv("ALERT_FROM", "dq-alerts@example.com")
    recipients = [a.strip() for a in os.getenv("ALERT_TO", "").split(",") if a.strip()]

    if not host or not recipients:
        log.warning("HIGH failures in %s but SMTP_HOST/ALERT_TO not set - alert not sent", run_id)
        return False

    msg = build_message(run_id, results, sender, recipients, report_path)
    port = int(os.getenv("SMTP_PORT", "587"))
    with smtp_cls(host, port, timeout=30) as smtp:
        smtp.starttls()
        user = os.getenv("SMTP_USER")
        if user:
            smtp.login(user, os.getenv("SMTP_PASSWORD", ""))
        smtp.send_message(msg)
    log.info("alert sent to %s", ", ".join(recipients))
    return True
