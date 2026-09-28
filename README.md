# JobPilot AI

A learning project for turning a resume into a reviewed career profile, then using it for job discovery, matching, and applications.

## Current milestone

Sprint 5 adds explainable job matching: compare your confirmed profile with saved jobs, review matched/missing skills and coverage, and refresh outdated results. Sprint 4 job intake and the earlier resume/profile workflows remain available.

**Current data flow:** PDF → original `raw_text` in `resumes` → Build draft → structured JSON in `resume_parses` → review and correct fields → explicitly confirm → independent JSON in `profiles` → Profile and Overview.

**Job data flow:** pasted email → original text and extraction draft in `job_imports` → review and confirm → independent fields in `jobs` → Job inbox. Manual entry saves directly to `jobs`.

**Matching flow:** confirmed profile skills + saved job skills → Find matches → versioned results in `job_matches` → ranked Matches page.

Automatic mailbox ingestion, AI tailoring, and application automation remain later milestones. A confirmed profile is never overwritten by rebuilding a parsed draft.

See the [Sprint 5 report](docs/SPRINT_5_REPORT.md) for scoring, snapshots, APIs, and validation. See the [Sprint 4 report](docs/SPRINT_4_REPORT.md) for the job workflow, tables, APIs, validation, and limitations. See the [Sprint 3 report](docs/SPRINT_3_REPORT.md) for the new table, workflow, API, and validation. The [Sprint 2 report](docs/SPRINT_2_REPORT.md) documents the parser, and the [Sprint 1 report](docs/SPRINT_1_REPORT.md) documents the foundation.

### Extraction quality update

Resume and job-email parsing now use version 2 rules, with layout-aware PDF reading, more common headings and entry formats, multiline email fields, and improved application-link selection. See the [extraction improvement report](docs/EXTRACTION_V2_REPORT.md) for supported formats, tests, and limitations.

For existing resumes, **Rebuild draft** updates parsing of stored text; **upload the PDF again** to use the improved PDF reading order. Pasting an identical unsaved job email again refreshes an older parser draft. Confirmed profiles and saved jobs are not overwritten.

## Requirements

- Node.js 22.12+ (the current Vite version requires a modern Node release).
- Python 3.11+; development was checked with Python 3.14.
- PostgreSQL 16. Docker Compose is provided for the database only.

## 1. Configure the environment

From the repository root, create your local files **only if they do not already exist**:

```sh
cp -n backend/.env.example backend/.env
cp -n frontend/.env.example frontend/.env
cp -n docker/.env.example docker/.env
```

Edit the local files:

- Set the same database username, password, database name, and port in the Docker and backend configurations. URL-encode special characters in the password in `DATABASE_URL`.
- Generate a strong `JWT_SECRET_KEY`, for example with `python3 -c 'import secrets; print(secrets.token_urlsafe(48))'`.
- Keep `JWT_ALGORITHM=HS256` and choose a token lifetime in minutes.
- Set `VITE_API_URL=http://localhost:8000` in `frontend/.env` to match the backend command below. If you choose a different backend port, update both settings and restart Vite.
- `CORS_ORIGINS` is a JSON array of allowed frontend origins. Both `localhost:5173` and `127.0.0.1:5173` are supported by default.
- Relative `UPLOAD_DIR` values resolve from `backend/`. The backend `.env` path is also independent of the current shell directory.

Local `.env` files and uploaded PDFs are excluded from Git. Never commit credentials or real resume files.

## 2. Start the database

From the repository root:

```sh
docker compose --env-file docker/.env -f docker/docker-compose.yml up -d
```

If you already have a database, keep its current configuration. Changing `POSTGRES_PASSWORD` does not reset the password of a database already initialized in a Docker volume. Do not delete an existing volume to resolve a configuration mismatch.

## 3. Run the backend

```sh
cd backend
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Skip virtual-environment creation if you already have `backend/venv`.

API documentation: [localhost:8000/docs](http://localhost:8000/docs).

### Migration notes

The migration head is `e05b3c742df6`. Run `python -m alembic upgrade head` to add `job_matches`, along with any earlier unapplied migrations. These migrations add tables; existing resume text and parsed drafts are not rewritten.

Two historical migrations were repaired for new databases and databases still on earlier revisions:

- `9b5bb8692d67` now renames `password` to `password_hash`, preserving values, and backfills `created_at` before removing its temporary server default. Downgrading preserves credential values too.
- `2770c292bcd8` explicitly names the foreign key `resumes_user_id_fkey`, matching PostgreSQL's original generated name, so downgrades can remove it reliably.

**Before upgrading a populated legacy database**, back it up and verify that its old `password` column contains supported password hashes. The migration preserves values; it does not guess whether a value is plaintext or invent a conversion. Argon2 and bcrypt hashes are supported. Unrecognized values are rejected at login and need a separate credential remediation plan. No migration changes were applied to your existing database during Sprint 1 verification.

Online and offline Alembic modes both use `DATABASE_URL`. To inspect generated SQL without changing a database:

```sh
python -m alembic upgrade head --sql
```

Do not replay an already-applied revision. The safety corrections do not change its revision ID.

## 4. Run the frontend

In a separate terminal:

```sh
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Open [localhost:5173](http://localhost:5173). Restart Vite if you change its environment variables or if it selects a different port; the API origin and CORS settings must agree.

## Using the application

1. Register an account. Successful registration takes you to sign-in with a confirmation.
2. Sign in. Protected requests use the stored bearer token; the account is restored on reload.
3. Open **My resume**, choose or drop a text-based PDF up to 5 MiB, then select **Upload & extract**.
4. Select a document under **Your saved resumes**, then choose **Build draft**.
5. Inspect contact details, summary, skills, experience, education, projects, warnings, and source blocks. **Rebuild draft** explicitly replaces the current draft.
6. Select **Review & confirm profile**. Correct contact details, summary, skills, experience, education, and projects. The original text and parser notes remain available for comparison.
7. Check the review confirmation and choose **Save confirmed profile**. Open **Profile** to see the result or **Edit profile** to update it. Overview displays counts from these confirmed details.
8. Open **Job inbox**. Add a job manually, or paste one job email, extract its draft, review the fields, check confirmation, and save. Pending imports can be reopened from the inbox. Saved jobs support search, filters, editing, and archiving.
9. Open **Matches** and choose **Find matches**. Inspect skill coverage and alias evidence. After profile/job edits, rerun matching to refresh outdated results. Archived jobs are excluded from runs.
10. Use the menu button in the top bar to open or close the sidebar. Mobile starts closed. Changes to the sidebar do not discard form edits.

Reviewing the same source resume loads your saved corrections. Reviewing a different resume starts from that draft and explicitly warns that saving will replace the current profile. Older tabs cannot overwrite newer profile saves: reload the latest version after a conflict. Unsaved edits are held in page memory, with warnings for route navigation and browser unload; there is no autosave or offline recovery.

Encrypted, empty, corrupt, oversized, and textless PDFs produce explicit errors. Scanned-image OCR is not implemented. The saved-resume selector lists the latest 50 uploads. The API supports `limit`/`offset` pagination. Missing or ambiguous fields remain empty, with source text preserved for review. The parser supports a limited set of English headings and layouts, not arbitrary resumes.

Signing out clears this browser's session; it does not revoke an already-issued token on the server. Password recovery and refresh tokens are not implemented.

## Verification

### Backend application tests

From `backend/`:

```sh
./venv/bin/python -m unittest discover -s tests -v
```

These tests use an in-memory SQLite database and temporary upload directories. They do not create users or upload documents in your configured database.

### Frontend checks

From `frontend/`:

```sh
npm test
npm run lint
npm run build
```

The frontend tests use Node's test runner and compile the real TypeScript modules in memory. No extra test framework dependency was added. Sprint 2 frontend tests cover authenticated history requests, separate source/draft retrieval, explicit rebuilding, failed parse responses, and initial panel state. Sprint 3 adds form conversion, independent source data, authenticated profile saving, error handling, and safe profile rendering tests. Sprint 4 adds job form conversion, authenticated intake and saving, revision checks, filter requests, duplicate responses, and a regression check against logging login credentials. Sprint 5 covers authenticated matching requests, score states, stale-result presentation, alias evidence, escaped content, and conflicts.

`npm test` runs the test files currently present in `frontend/tests`. The previously deleted Sprint 1 frontend test file was not restored during Sprint 2.

### Optional PostgreSQL migration integration tests

Use a disposable database; the suite upgrades and downgrades it. It refuses non-loopback hosts and database names other than `jobpilot_test`.

```sh
docker run --rm -d --name jobpilot-sprint1-migration-test \
  -e POSTGRES_USER=jobpilot_test \
  -e POSTGRES_PASSWORD=local-test-only \
  -e POSTGRES_DB=jobpilot_test \
  -p 127.0.0.1:15432:5432 postgres:16
```

Wait until PostgreSQL is ready (`docker exec jobpilot-sprint1-migration-test pg_isready -U jobpilot_test`), then from `backend/`:

```sh
JOBPILOT_TEST_DATABASE_URL=postgresql+psycopg://jobpilot_test:local-test-only@127.0.0.1:15432/jobpilot_test \
  ./venv/bin/python -m unittest discover -s tests -p test_postgres_migrations.py -v
```

Clean up this disposable container after testing:

```sh
docker stop jobpilot-sprint1-migration-test
```

Ordinary backend test discovery skips these seven tests unless the explicit test URL is provided.

## Code map

- `backend/app/api/routes`: HTTP endpoints and response contracts.
- `backend/app/services`: authentication, upload orchestration, PDF extraction, rule-based resume/job parsing, confirmed-profile saving, job intake/saving, and deterministic skill matching.
- `backend/app/repositories`: database persistence and owner-scoped resume, profile, and job queries.
- `backend/app/models` and `schemas`: database entities and validated API data.
- `frontend/src/contexts`: user/session state.
- `frontend/src/api` and `services`: API client and endpoint calls.
- `frontend/src/components/ui`: reusable icons, page headings, and planned-feature states.
- `frontend/src/styles.css`: shared design tokens, page layouts, and responsive styles.

## Known boundaries

The upload service handles ordinary exceptions by rolling back database work and deleting the failed upload. A process crash or an ambiguous database connection failure at commit time can still require storage reconciliation; there is no background cleanup worker yet. File bytes are read in bounded chunks by the service, but production request-size/time limits still belong at the server/proxy boundary.

The application is a local learning project, not a deployment-ready authentication platform. Production hardening, rate limiting, token revocation, backups, and deployment configuration are separate work. The empty `backend/Dockerfile` directory from the original scaffold is not a container build definition.
