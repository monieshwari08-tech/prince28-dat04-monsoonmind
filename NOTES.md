Day 2 – Database Migrations

3134f8dd9f33 -> c41df4754b2a (head), add gin index on metadata

<base> -> 3134f8dd9f33, create documents and pages


Day 3 – Idempotent Loader Test Results

Run 1:
records=21 inserted=0 updated=0 unchanged=21

Run 2 (after changing record 021 rainfall_mm from 345.5 to 346.5):
records=21 inserted=0 updated=1 unchanged=20

Run 3:
records=21 inserted=0 updated=0 unchanged=21
