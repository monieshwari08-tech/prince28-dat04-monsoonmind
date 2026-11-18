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

Day 3 – EXPLAIN ANALYZE Results

Query:
SELECT id, title FROM documents
WHERE metadata @> '{"season": "Southwest Monsoon"}'::jsonb;

Normal planner:
Seq Scan on documents
Actual rows: 5
Rows removed by filter: 16
Execution time: 1.087 ms

With enable_seqscan = off:
Bitmap Heap Scan on documents
  Bitmap Index Scan on ix_documents_metadata_gin
Actual rows: 5
Execution time: 1.547 ms

Conclusion:
PostgreSQL chose a sequential scan because the table contains only 21 records, making a full scan cheaper. When sequential scans were disabled, PostgreSQL used the GIN index successfully. This confirms that the metadata GIN index is working.
