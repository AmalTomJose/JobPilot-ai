# JobPilot AI

A learning project for turning a resume into a reviewed career profile, then using it for job discovery, matching, and applications.

## Current milestone

Sprint 1 implements account registration/sign-in, authenticated PDF uploads, text extraction, and a responsive application shell. The dashboard guides the next step; Profile shows real account details. Jobs and Applications are clearly labeled as planned features.

**Current data flow:** PDF → local file → PyMuPDF text extraction → one database transaction containing file metadata and `raw_text` → upload confirmation and text preview.

Structured resume parsing, editable extraction review, saved professional profiles, upload history, job ingestion, matching, AI tailoring, and application automation are later milestones.

See [Sprint 1 report](docs/SPRINT_1_REPORT.md) for changes and verification.

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
- `frontend/.env` points at `http://localhost:8001`. Port 8001 avoids an existing local service on 8000.
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
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Skip virtual-environment creation if you already have `backend/venv`.

API documentation: [localhost:8001/docs](http://localhost:8001/docs).

### Migration notes

The migration head remains `767a67c5e23e`; Sprint 1 does not introduce new tables or require a new migration for an already-current database.

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
4. Review the success message and expand **Preview extracted text**.
5. Open **Profile** for current account details, or **Settings** to sign out.

Encrypted, empty, corrupt, oversized, and textless PDFs produce explicit errors. Scanned-image OCR is not implemented. Upload history is not available yet: files and text remain saved, but the current preview is component state and disappears after leaving the page or reloading.

Signing out clears this browser's session; it does not revoke an already-issued token on the server. Password recovery and refresh tokens are not implemented.

## Verification

### Backend application tests

From `backend/`:

```sh
./venv/bin/python -m unittest discover -s tests -p test_sprint1.py -v
```

These tests use an in-memory SQLite database and temporary upload directories. They do not create users or upload documents in your configured database.

### Frontend checks

From `frontend/`:

```sh
npm test
npm run lint
npm run build
```

The frontend tests use Node's test runner and compile the real TypeScript modules in memory. No extra test framework dependency was added. Tests cover request authentication, session expiry, network failures, registration payloads, validation, and masked passwords.

The pre-existing `tests/neon-coast.test.cjs` file is unrelated to JobPilot and points at a missing game asset. It was left intact; `npm test` deliberately runs the JobPilot suite only.

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

Ordinary backend test discovery skips these three tests unless the explicit test URL is provided.

## Code map

- `backend/app/api/routes`: HTTP endpoints and response contracts.
- `backend/app/services`: authentication, upload orchestration, PDF extraction.
- `backend/app/repositories`: database persistence and owner-scoped resume queries.
- `backend/app/models` and `schemas`: database entities and validated API data.
- `frontend/src/contexts`: user/session state.
- `frontend/src/api` and `services`: API client and endpoint calls.
- `frontend/src/components/ui`: reusable icons, page headings, and planned-feature states.
- `frontend/src/styles.css`: shared design tokens, page layouts, and responsive styles.

## Known boundaries

The upload service handles ordinary exceptions by rolling back database work and deleting the failed upload. A process crash or an ambiguous database connection failure at commit time can still require storage reconciliation; there is no background cleanup worker yet. File bytes are read in bounded chunks by the service, but production request-size/time limits still belong at the server/proxy boundary.

The application is a local learning project, not a deployment-ready authentication platform. Production hardening, rate limiting, token revocation, backups, and deployment configuration are separate work. The empty `backend/Dockerfile` directory from the original scaffold is not a container build definition.
