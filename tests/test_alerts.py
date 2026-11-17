import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dq_framework import alerts  # noqa: E402

FAIL = {"dataset_name": "claims", "rule_name": "claim_id_unique", "severity": "HIGH",
        "status": "FAIL", "message": "2 of 120 records failed"}
LOW_FAIL = {**FAIL, "rule_name": "zip_format", "severity": "LOW"}


class FakeSMTP:
    sent = []

    def __init__(self, host, port, timeout=None):
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self):
        pass

    def login(self, user, pwd):
        self.user = user

    def send_message(self, msg):
        FakeSMTP.sent.append(msg)


def test_no_alert_when_only_low_failures(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("ALERT_TO", "team@example.com")
    assert alerts.send_alert("R1", [LOW_FAIL], smtp_cls=FakeSMTP) is False


def test_no_smtp_configured_just_logs(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    assert alerts.send_alert("R1", [FAIL], smtp_cls=FakeSMTP) is False


def test_sends_with_report_attached(monkeypatch, tmp_path):
    FakeSMTP.sent.clear()
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("ALERT_TO", "a@example.com, b@example.com")
    report = tmp_path / "dq_report_R1.html"
    report.write_text("<html></html>")

    assert alerts.send_alert("R1", [FAIL, LOW_FAIL], report_path=report, smtp_cls=FakeSMTP) is True
    msg = FakeSMTP.sent[0]
    assert msg["Subject"].startswith("[DQ] 1 HIGH")
    assert msg["To"] == "a@example.com, b@example.com"
    assert "claims.claim_id_unique" in msg.get_body(("plain",)).get_content()
    assert any(p.get_filename() == "dq_report_R1.html" for p in msg.iter_attachments())
