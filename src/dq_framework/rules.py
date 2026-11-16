"""
Rule library.

Each rule takes a DataFrame + column + params and returns a boolean
Series where True = record FAILED the check. Keeping the same signature
for every rule is what lets the engine stay generic - it just looks
the function up by rule_type from the config table.
"""
import re
from datetime import date

import pandas as pd


def _is_blank(s: pd.Series) -> pd.Series:
    return s.isna() | (s.astype(str).str.strip() == "")


def not_null(df, column, params, context=None):
    return _is_blank(df[column])


def unique(df, column, params, context=None):
    s = df[column]
    # blanks are handled by not_null, don't double count them here
    return s.duplicated(keep=False) & ~_is_blank(s)


def allowed_values(df, column, params, context=None):
    allowed = set(params.get("values", []))
    return ~df[column].isin(allowed) & ~_is_blank(df[column])


def regex(df, column, params, context=None):
    pattern = re.compile(params["pattern"])
    s = df[column].astype(str)
    return ~s.apply(lambda v: bool(pattern.match(v)))


def range_check(df, column, params, context=None):
    values = pd.to_numeric(df[column], errors="coerce")
    low = params.get("min", float("-inf"))
    high = params.get("max", float("inf"))
    return values.isna() | (values < low) | (values > high)


def date_not_future(df, column, params, context=None):
    dates = pd.to_datetime(df[column], errors="coerce")
    today = pd.Timestamp(date.today())
    return dates.isna() | (dates > today)


def referential(df, column, params, context=None):
    """Every value must exist in another dataset (like a foreign key)."""
    if context is None or params["ref_dataset"] not in context:
        raise ValueError(f"reference dataset {params.get('ref_dataset')} not loaded")
    ref_df = context[params["ref_dataset"]]
    ref_values = set(ref_df[params["ref_column"]].dropna().astype(str))
    return ~df[column].astype(str).isin(ref_values)


def row_count(df, column, params, context=None):
    """Dataset-level check. Returns a single-row result: fail if too few rows."""
    min_rows = params.get("min_rows", 1)
    return pd.Series([len(df) < min_rows])


# rule_type (from dq_rule_config) -> function
RULE_REGISTRY = {
    "not_null": not_null,
    "unique": unique,
    "allowed_values": allowed_values,
    "regex": regex,
    "range": range_check,
    "date_not_future": date_not_future,
    "referential": referential,
    "row_count": row_count,
}


def get_rule(rule_type):
    try:
        return RULE_REGISTRY[rule_type]
    except KeyError:
        raise ValueError(f"Unknown rule_type '{rule_type}'. Known: {sorted(RULE_REGISTRY)}")
