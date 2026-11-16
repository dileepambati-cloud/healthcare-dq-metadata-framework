-- Sample config: two healthcare datasets and the rules we run on them.
-- Data is synthetic (see data/sample). Adding a new check = inserting a row here.

INSERT INTO dq_dataset_config VALUES
 (1, 'members', 'ELIGIBILITY', 'csv', 'data/sample/members.csv', 'FULL',        'data-team@example.com', 'Y'),
 (2, 'claims',  'CLAIMS',      'csv', 'data/sample/claims.csv',  'INCREMENTAL', 'data-team@example.com', 'Y');

INSERT INTO dq_rule_config VALUES
 -- members
 (101, 1, 'member_id_not_null',     'not_null',       'member_id',   '{}',                                           'HIGH',   100.00, 'Y'),
 (102, 1, 'member_id_unique',       'unique',         'member_id',   '{}',                                           'HIGH',   100.00, 'Y'),
 (103, 1, 'gender_valid_values',    'allowed_values', 'gender',      '{"values": ["M", "F", "U"]}',                  'MEDIUM', 100.00, 'Y'),
 (104, 1, 'zip_code_format',        'regex',          'zip_code',    '{"pattern": "^[0-9]{5}$"}',                    'LOW',     95.00, 'Y'),
 (105, 1, 'dob_not_in_future',      'date_not_future','date_of_birth','{}',                                          'HIGH',   100.00, 'Y'),
 -- claims
 (201, 2, 'claim_id_not_null',      'not_null',       'claim_id',    '{}',                                           'HIGH',   100.00, 'Y'),
 (202, 2, 'claim_id_unique',        'unique',         'claim_id',    '{}',                                           'HIGH',   100.00, 'Y'),
 (203, 2, 'paid_amount_range',      'range',          'paid_amount', '{"min": 0, "max": 100000}',                    'HIGH',    99.00, 'Y'),
 (204, 2, 'claim_status_valid',     'allowed_values', 'claim_status','{"values": ["PAID", "DENIED", "PENDING"]}',    'MEDIUM', 100.00, 'Y'),
 (205, 2, 'member_exists',          'referential',    'member_id',   '{"ref_dataset": "members", "ref_column": "member_id"}', 'HIGH', 100.00, 'Y'),
 (206, 2, 'claims_min_row_count',   'row_count',      NULL,          '{"min_rows": 10}',                             'MEDIUM', 100.00, 'Y');
