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

Why did the planner choose a Seq Scan?
The table contains only 21 records, so scanning all rows is cheaper.
The planner estimates a sequential scan will be faster for this small table.

When would it switch to the GIN index?
When the table grows and the planner estimates that using the GIN index is cheaper for the filter.

## Day 4 – Docker, Compose and Tests

### Clean clone verification

- Cloned the repository from GitHub into a fresh folder.
- Copied .env.example to .env.
- docker compose up --build completed successfully.
- Verified using a separate Compose project name and fresh database volume.
- PostgreSQL and Redis became healthy.
- Fresh migrations completed successfully.
- Sample records: 21 inserted=21, updated=0, unchanged=0.
- API /ready returned HTTP 200 OK.
- Clean clone startup and fresh database verification passed.

### Docker image

- Image: monsoonmind:dev
- Size: approximately 70 MB (target: under 400 MB)
- Container runs as non-root user: uid=999(app), gid=999(app).
- Dependency installation layer is cached when pyproject.toml and uv.lock remain unchanged.

### Docker Compose stack

- PostgreSQL with pgvector: healthy
- Redis: healthy
- Migration service: exited with code 0
- API: healthy
- Sample records loaded: 21

First load:
records=21 inserted=21 updated=0 unchanged=0

Second load:
records=21 inserted=0 updated=0 unchanged=21

### Database failure and recovery

Database stopped:
- /health: HTTP 200 OK — {"status":"ok","app":"monsoonmind","env":"local"}
- /ready: HTTP 503 Service Unavailable — {"status":"not_ready","checks":{"database":false}}

Database restarted:
- /ready: HTTP 200 OK — {"status":"ready","checks":{"database":true}}

Database stopped:
- /health: {"status":"ok","app":"monsoonmind","env":"local"}
- /ready: {"status":"not_ready","checks":{"database":false}}

Database restarted:
- /ready: {"status":"ready","checks":{"database":true}}

A load balancer should stop sending traffic when readiness fails because the database is unavailable. The application should not restart because its process is still healthy.

### Tests and coverage

- Unit tests: 16 passed
- Integration tests: 7 passed
- Unit-only coverage: 83%
- Coverage with integration tests: 92%

Total tests with integration: 23 passed.

### Coverage observations

Some logging and middleware lines were not exercised by the tests. These are areas where additional tests could improve coverage; uncovered lines do not automatically indicate bugs.
### Clean clone verification

- Cloned the repository from GitHub into a fresh folder.
- Copied .env.example to .env.
- docker compose up --build completed successfully.
- Used a separate Compose project name and fresh database volume.
- PostgreSQL and Redis became healthy.
- Fresh migrations completed successfully.
- Sample records: 21 inserted=21, updated=0, unchanged=0.
- API /ready returned HTTP 200 OK.
- Clean clone startup and fresh database verification passed.
