## D03 - PostgreSQL and Database Evidence
Day 2 â€“ Database Migrations

3134f8dd9f33 -> c41df4754b2a (head), add gin index on metadata
<base> -> 3134f4754b2a, create documents and pages
Day 3 â€“ Idempotent Loader Test Results

Run 1:
records=21 inserted=0 updated=0 unchanged=21

Run 2 (after changing record 021 rainfall_mm from 345.5 to 346.5):
records=21 inserted=0 updated=1 unchanged=20

Run 3:
records=21 inserted=0 updated=0 unchanged=21

Day 3 â€“ EXPLAIN ANALYZE Results

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
Day 4 â€“ Docker, Compose and Tests
Clean clone verification
- Cloned the repository from GitHub into a fresh folder.
- Copied .env.example to .env.
- docker compose up --build completed successfully.
- Verified using a separate Compose project name and fresh database volume.
- PostgreSQL and Redis became healthy.
- Fresh migrations completed successfully.
- Sample records: 21 inserted=21, updated=0, unchanged=0.
- API /ready returned HTTP 200 OK.
- Clean clone startup and fresh database verification passed.
Docker image
- Image: monsoonmind:dev
- Size: approximately 70 MB (target: under 400 MB)
- Container runs as non-root user: uid=999(app), gid=999(app).
- Dependency installation layer is cached when pyproject.toml and uv.lock remain unchanged.
Docker Compose stack
- PostgreSQL with pgvector: healthy
- Redis: healthy
- Migration service: exited with code 0
- API: healthy
- Sample records loaded: 21
First load:
records=21 inserted=21 updated=0 unchanged=0

Second load:
records=21 inserted=0 updated=0 unchanged=21
Database failure and recovery
Database stopped:
- /health: HTTP 200 OK â€” {"status":"ok","app":"monsoonmind","env":"local"}
- /ready: HTTP 503 Service Unavailable â€” {"status":"not_ready","checks":{"database":false}}
Database restarted:
- /ready: HTTP 200 OK â€” {"status":"ready","checks":{"database":true}}
Database stopped:
- /health: {"status":"ok","app":"monsoonmind","env":"local"}
- /ready: {"status":"not_ready","checks":{"database":false}}
Database restarted:
- /ready: {"status":"ready","checks":{"database":true}}
A load balancer should stop sending traffic when readiness fails because the database is unavailable. The application should not restart because its process is still healthy.
Tests and coverage
- Unit tests: 16 passed
- Integration tests: 7 passed
- Unit-only coverage: 83%
- Coverage with integration tests: 92%
Total tests with integration: 23 passed.
Coverage observations
Some logging and middleware lines were not exercised by the tests. These are areas where additional tests could improve coverage; uncovered lines do not automatically indicate bugs.
Clean clone verification
- Cloned the repository from GitHub into a fresh folder.
- Copied .env.example to .env.
- docker compose up --build completed successfully.
- Used a separate Compose project name and fresh database volume.
- PostgreSQL and Redis became healthy.
- Fresh migrations completed successfully.
- Sample records: 21 inserted=21, updated=0, unchanged=0.
- API /ready returned HTTP 200 OK.
- Clean clone startup and fresh database verification passed.
## D05 - CI/CD, Deployment, Rollback and Monitoring
Day 5 - CI, Deployment, Rollback and Monitoring
Production deployment
- Live URL: https://monsoonmind.onrender.com
- API documentation: https://monsoonmind.onrender.com/docs
- Health endpoint: https://monsoonmind.onrender.com/health
- Readiness endpoint: https://monsoonmind.onrender.com/ready
CI and automatic deployment
- CI workflow: https://github.com/monieshwari08-tech/prince28-dat04-monsoonmind/actions/workflows/ci.yml
- CD workflow: https://github.com/monieshwari08-tech/prince28-dat04-monsoonmind/actions/workflows/cd.yml
- First successful automatic deployment: CD #1
- CD #1 commit: 87906142fe3df05fc2b8bfee5f8c886b166f18fc
- CD #1 result: Success (45 seconds)
- Smoke test: Passed
- Health: Production OK
- Readiness: Ready (database=True)
- Documents endpoint: OK
Roll-forward verification
- CD #4 result: Success (29 seconds)
- Roll-forward version: ebc9e78314c5205007e2c7be9e4e2d49a2b35d9e
- Health: Production OK
- Readiness: Ready (database=True)
- Documents endpoint: OK
- Smoke test: Passed
Latest deployment
- CD #5 result: Success (31 seconds)
- Deployed version: a6c92cf8862449799a5456b789a2cace0571d773
- Health: Production OK
- Readiness: Ready (database=True)
- Documents endpoint: OK
- Smoke test: Passed
Rollback drill
- Rollback target version: 87906142fe3df05fc2b8bfee5f8c886b166f18fc
- CD #3 initial smoke test reported a version mismatch because the live deployment had not finished switching.
- The live /health endpoint subsequently confirmed the rollback target version.
- Database schema was not downgraded during rollback; only the application image was changed.
- Rollbacks are safe only when the newer database schema remains backward-compatible with the older application version.
Monitoring and nightly health check
- UptimeRobot monitor: https://monsoonmind.onrender.com/health
- Check interval: Every 5 minutes
- Monitor status: Up
- Nightly GitHub Actions workflow: Nightly Health Check
- Schedule: 18:30 UTC (00:00 IST)
- Manual nightly health check: Successful
- Email alert configuration: Not yet verified
Secrets
- GitHub Actions secrets: RENDER_DEPLOY_HOOK, DATABASE_URL
- GitHub Actions variable: LIVE_URL
- Render environment variables: APP_ENV, DATABASE_URL
- Secret values are not stored in this file.
Performance improvement
Render Free services can sleep after inactivity. A future improvement is to optimize application startup and reduce cold-start time.
Remaining timing details
Exact merge time, smoke-test completion time, rollback time and roll-forward time should be recorded from the corresponding GitHub Actions run timestamps.
Final Engineering Improvements - 22 November 2026
100% Test Coverage Achievement
Final GitHub Actions CI results:
- Total statements: 259
- Missing statements: 0
- Total branches: 30
- Partially covered branches: 0
- Total coverage: 100%
- Tests passed: 39
- Test execution time: 3.94 seconds
- Files with complete coverage: 16
Coverage Improvement History
Milestone	Coverage	Tests
Initial baseline	92%	23
Logging improvements	97%	29
Middleware improvements	98%	34
Repository improvements	99%	38
Database dependency improvements	100%	39


Additional Testing Improvements
- Added logging setup tests.
- Added middleware request ID and exception-handling tests.
- Added repository boolean and decimal conversion tests.
- Added repository missing-document tests.
- Added database dependency failure test.
- Achieved 100% statement and branch coverage.
Relevant Commits
- Middleware logging tests: e8ec94e
- Repository coverage tests: a2716e6
- Database dependency failure test: 04a7dba
Final Validation
- Ruff lint: Passed.
- Ruff formatting: Passed.
- Pre-commit hooks: Passed.
- GitHub Actions CI: Passed.
- Total coverage: 100%.
- Tests passed: 39.
The earlier Day 4 coverage figures are historical results. This final report supersedes those measurements.
