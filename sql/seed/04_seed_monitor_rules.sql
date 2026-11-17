-- Dataset-level monitors. column_name is the timestamp column for
-- freshness and NULL for the others.

INSERT INTO dq_rule_config VALUES
 (107, 1, 'members_schema_drift',  'schema_drift',   NULL,          '{}',                                        'HIGH',   100.00, 'Y'),
 (108, 1, 'members_volume_check',  'volume_anomaly', NULL,          '{"lookback_runs": 7, "tolerance_pct": 30}', 'MEDIUM', 100.00, 'Y'),
 (207, 2, 'claims_freshness',      'freshness',      'service_date','{"max_age_hours": 8760}',                   'HIGH',   100.00, 'Y'),
 (208, 2, 'claims_schema_drift',   'schema_drift',   NULL,          '{}',                                        'HIGH',   100.00, 'Y'),
 (209, 2, 'claims_volume_check',   'volume_anomaly', NULL,          '{"lookback_runs": 7, "tolerance_pct": 30}', 'MEDIUM', 100.00, 'Y');
