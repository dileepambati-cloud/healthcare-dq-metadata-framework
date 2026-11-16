-- =====================================================================
-- Metadata tables for the data quality framework
-- Every check is driven from these tables - no hard-coded rules in code.
-- Written in ANSI-ish SQL so it runs on SQLite locally and Snowflake.
-- =====================================================================

-- Which datasets (tables/files) are under DQ monitoring
CREATE TABLE IF NOT EXISTS dq_dataset_config (
    dataset_id        INTEGER      PRIMARY KEY,
    dataset_name      VARCHAR(100) NOT NULL,     -- logical name e.g. claims
    source_system     VARCHAR(50),               -- e.g. CLAIMS_ORACLE
    source_type       VARCHAR(20)  NOT NULL,     -- csv | table
    source_location   VARCHAR(500) NOT NULL,     -- file path or db.schema.table
    load_type         VARCHAR(20)  DEFAULT 'FULL', -- FULL | INCREMENTAL
    owner_email       VARCHAR(200),
    is_active         CHAR(1)      DEFAULT 'Y'
);

-- One row per rule. rule_type maps to a function in rules.py
CREATE TABLE IF NOT EXISTS dq_rule_config (
    rule_id           INTEGER      PRIMARY KEY,
    dataset_id        INTEGER      NOT NULL,
    rule_name         VARCHAR(100) NOT NULL,
    rule_type         VARCHAR(50)  NOT NULL,     -- not_null, unique, range ...
    column_name       VARCHAR(100),
    rule_params       VARCHAR(1000),             -- JSON string of params
    severity          VARCHAR(10)  DEFAULT 'HIGH', -- HIGH | MEDIUM | LOW
    threshold_pct     DECIMAL(5,2) DEFAULT 100.00, -- min pass % to call it PASS
    is_active         CHAR(1)      DEFAULT 'Y',
    FOREIGN KEY (dataset_id) REFERENCES dq_dataset_config(dataset_id)
);

-- One row per execution of the framework
CREATE TABLE IF NOT EXISTS dq_run_log (
    run_id            VARCHAR(50)  PRIMARY KEY,
    run_start_ts      TIMESTAMP,
    run_end_ts        TIMESTAMP,
    datasets_checked  INTEGER,
    rules_executed    INTEGER,
    rules_failed      INTEGER,
    run_status        VARCHAR(20)                -- SUCCESS | FAILED | WARN
);

-- One row per rule per run - this is what reports / dashboards read
CREATE TABLE IF NOT EXISTS dq_result_log (
    run_id            VARCHAR(50)  NOT NULL,
    rule_id           INTEGER      NOT NULL,
    dataset_name      VARCHAR(100),
    rule_name         VARCHAR(100),
    column_name       VARCHAR(100),
    total_records     INTEGER,
    failed_records    INTEGER,
    pass_pct          DECIMAL(6,2),
    status            VARCHAR(10),               -- PASS | FAIL
    severity          VARCHAR(10),
    message           VARCHAR(1000),
    checked_ts        TIMESTAMP
);
