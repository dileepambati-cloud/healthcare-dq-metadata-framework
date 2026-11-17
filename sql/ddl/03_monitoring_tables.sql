-- =====================================================================
-- Tables used by the dataset-level monitors (volume + schema drift).
-- These keep history between runs so we can compare today vs normal.
-- =====================================================================

-- Row count captured on every run, per dataset.
-- volume_anomaly compares the current count to the recent average.
CREATE TABLE IF NOT EXISTS dq_volume_history (
    dataset_name      VARCHAR(100) NOT NULL,
    run_id            VARCHAR(50)  NOT NULL,
    row_count         INTEGER      NOT NULL,
    captured_ts       TIMESTAMP    NOT NULL
);

-- Expected columns for each dataset. First run with no baseline
-- records one; after that, any added / removed / retyped column is drift.
CREATE TABLE IF NOT EXISTS dq_schema_baseline (
    dataset_name      VARCHAR(100) NOT NULL,
    column_name       VARCHAR(100) NOT NULL,
    data_type         VARCHAR(50),
    ordinal_position  INTEGER,
    captured_ts       TIMESTAMP,
    PRIMARY KEY (dataset_name, column_name)
);
