## D03 - PostgreSQL and Database Evidence
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
Day 4 – Docker, Compose and Tests
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


## D06 · Collecting the corpus

- Start target: 10 years of NE monsoon reports + 20 cyclone reports.
- Final dataset report: 35 PDF files, 4,466 pages, 500.99 MB; 4,162 pages have extractable text.
- The earlier Day 4 coverage figures are historical results. This final report supersedes those measurements.
- Doors used: manually collected source URL lists and official IMD/RSMC archive pages.

### Licence check

| Source | Licence or terms, in my words | May I show full text in answers? |
|---|---|---|
| IMD Chennai / MetNet | Public IMD publications; copyright applies; reuse permission not confirmed | No, not without permission review |
| IMD RSMC | Public IMD publications; copyright applies; reuse permission not confirmed | No, not without permission review |
| Open-Meteo | CC BY 4.0 data terms | Follow attribution and licence terms |

### robots.txt

Checked on 2026-11-26:

| Domain | robots.txt result |
|---|---|
| mausam.imd.gov.in | HTTP 404 Not Found |
| rsmcnewdelhi.imd.gov.in | HTTP 404 Not Found |
| api.imd.gov.in | HTTP 404 Not Found |

- No robots.txt directives were available at these URLs on the check date.
- A 404 response is not permission to crawl or reuse content.
- Keep requests polite, rate-limited, and subject to manual licence review.
- Check the manifest and fetch logs for actual blocked-request outcomes.

### Kill and resume

- Run 1: interrupted with Ctrl+C after 4 files.
- Run 2: downloaded=6, skipped=4.
- Run 3: downloaded=0, skipped=10.
- Deleted-file recovery test: downloaded=1, skipped=9.
- Earlier partial-file check: no `.part` files remained.

### Capacity

- Measured corpus: 4,466 pages; 4,162 pages have extractable text.
- Estimated tokens per page: 318 (extracted characters divided by 4).
- Full 4,000-page target: 1.27 M tokens, 2,544 chunks, embedding about Rs 24.16, vectors 9.94 MB.

### One thing that went wrong today, and how I fixed it

- Some PDFs produced fontTools encoding warnings. The report completed and all 51 unit tests passed.

- Final dataset report confirms 35 PDFs, 4,466 pages, and 500.99 MB; 4,162 pages have extractable text.

## D07 - PDF Parser Comparison

Compared PyMuPDF and pypdf on the 10 largest downloaded PDF files.
Page counts matched for all 10 files.

| PDF file | Pages (PyMuPDF/pypdf) | PyMuPDF chars | pypdf chars | Observation |
|---|---:|---:|---:|---|
| 27-81bdf0-rsmc-report-2021-a1ac4b0b.pdf | 345/345 | 552471 | 546439 | PyMuPDF extracted more characters |
| ar2017-44b0d87d.pdf | 144/144 | 342336 | 343806 | pypdf extracted more characters |
| 27-4e1280-rsmc-2014-4155ff27.pdf | 241/241 | 313192 | 310625 | PyMuPDF extracted more characters |
| annual-report2016english-aa1b0960.pdf | 142/142 | 342091 | 341620 | PyMuPDF extracted more characters |
| 27-bbaf11-rsmc-2017-438e4fd0.pdf | 328/328 | 416994 | 412920 | PyMuPDF extracted more characters |
| 27-9bbd0d-rsmc-2015-84120eb6.pdf | 338/338 | 382254 | 378275 | PyMuPDF extracted more characters |
| 27-2f6165-rsmc-2011-c91bde82.pdf | 186/186 | 197434 | 194457 | PyMuPDF extracted more characters |
| ne-monsoon-2023-51d18bec.pdf | 85/85 | 89624 | 89081 | PyMuPDF extracted more characters |
| ne-monsoon-2022-32b05142.pdf | 66/66 | 69121 | 68615 | PyMuPDF extracted more characters |
| ne-monsoon-2021-3952a738.pdf | 63/63 | 60160 | 59682 | PyMuPDF extracted more characters |

### Comparison conclusion

- Both parsers successfully opened all 10 selected PDFs.
- Extracted page counts matched in every file.
- PyMuPDF produced more extracted characters in 9 files; pypdf produced more in 1.
- Character count is a quantitative comparison, not proof of semantic accuracy. Text order, headings, tables, and encoding still require inspection.
- PyMuPDF emitted a malformed-PDF stitching warning on one report. pypdf emitted font encoding warnings on a report.
- Current ingestion uses PyMuPDF. Keep it as the primary parser and use pypdf as a comparison/fallback candidate; inspect problematic pages before changing parser selection.

### D07 parsing outcome and known limitation

- Neon database verification: 49 documents, 3,831 parsed pages, and 5 parse failures.
- All 5 failures are scanned image-only PDFs from the IMD RSMC corpus.
- The affected PDFs contain 296 pages in total; PyMuPDF and pypdf both returned almost no extractable text.
- Tesseract OCR is not installed in the parsing environment. These files remain recorded as `no_text_layer`; they are not counted as successfully parsed.
- OCR remains future work. No OCR output has been added to the database.
