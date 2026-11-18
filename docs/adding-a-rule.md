# Adding checks

## 1. Add a check to an existing dataset (no code)

Most new checks are just a row in `dq_rule_config`. Example - make sure every claim
has a service date that isn't in the future:

```sql
INSERT INTO dq_rule_config VALUES
 (210, 2, 'service_date_not_future', 'date_not_future', 'service_date', '{}', 'HIGH', 100.00, 'Y');
```

| column | notes |
|---|---|
| `rule_id` | unique; I keep 1xx for members, 2xx for claims |
| `dataset_id` | from `dq_dataset_config` |
| `rule_type` | one of the types in the README |
| `column_name` | column to check, `NULL` for dataset-level checks |
| `rule_params` | JSON string, `'{}'` if the rule takes none |
| `severity` | `HIGH` fails the run, `MEDIUM` / `LOW` only warn |
| `threshold_pct` | minimum pass % to count as PASS (100 = no bad rows allowed) |
| `is_active` | set to `'N'` to switch a check off without deleting it |

## 2. Add a new dataset

```sql
INSERT INTO dq_dataset_config VALUES
 (3, 'providers', 'PROVIDER_DB', 'oracle', 'PROV_OWNER.PROVIDERS', 'FULL', 'data-team@example.com', 'Y');
```

Then add rules for `dataset_id = 3` as above. For `oracle` / `snowflake` sources the
connection settings come from environment variables (see `.env.example`).

## 3. Add a new rule type (code)

1. Write a function in `src/dq_framework/rules.py` with the standard signature and
   return a boolean Series where `True` means the row failed:

   ```python
   def max_length(df, column, params, context=None):
       limit = int(params["max"])
       return df[column].astype(str).str.len() > limit
   ```

   Dataset-level checks go in `monitors.py` and return `(mask, message)` instead.

2. Register it:

   ```python
   RULE_REGISTRY["max_length"] = max_length
   ```

3. Add a test in `tests/test_rules.py`, then use it from config:

   ```sql
   INSERT INTO dq_rule_config VALUES
    (109, 1, 'last_name_max_length', 'max_length', 'last_name', '{"max": 50}', 'LOW', 100.00, 'Y');
   ```

The engine picks it up on the next run - nothing else changes.
