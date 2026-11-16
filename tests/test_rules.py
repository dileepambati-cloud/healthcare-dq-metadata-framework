import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dq_framework import rules  # noqa: E402


@pytest.fixture
def df():
    return pd.DataFrame({
        "id": ["1", "2", "2", "", "5"],
        "gender": ["M", "F", "X", "M", ""],
        "zip": ["60616", "6061", "38018", "abcde", "10001"],
        "amount": ["10", "-5", "200", "abc", "50"],
        "dob": ["1990-01-01", "2099-01-01", "1985-06-30", "bad-date", "2000-12-12"],
    })


def test_not_null(df):
    assert rules.not_null(df, "id", {}).sum() == 1


def test_unique_ignores_blanks(df):
    assert rules.unique(df, "id", {}).sum() == 2  # both "2"s flagged


def test_allowed_values(df):
    assert rules.allowed_values(df, "gender", {"values": ["M", "F", "U"]}).sum() == 1


def test_regex(df):
    assert rules.regex(df, "zip", {"pattern": r"^[0-9]{5}$"}).sum() == 2


def test_range(df):
    # -5 below min, 200 above max, 'abc' not numeric
    assert rules.range_check(df, "amount", {"min": 0, "max": 100}).sum() == 3


def test_date_not_future(df):
    assert rules.date_not_future(df, "dob", {}).sum() == 2


def test_referential():
    child = pd.DataFrame({"member_id": ["A", "B", "Z"]})
    parent = pd.DataFrame({"member_id": ["A", "B"]})
    failed = rules.referential(child, "member_id",
                               {"ref_dataset": "members", "ref_column": "member_id"},
                               context={"members": parent})
    assert failed.sum() == 1


def test_row_count(df):
    assert rules.row_count(df, None, {"min_rows": 10}).sum() == 1
    assert rules.row_count(df, None, {"min_rows": 3}).sum() == 0


def test_unknown_rule_type():
    with pytest.raises(ValueError):
        rules.get_rule("does_not_exist")
