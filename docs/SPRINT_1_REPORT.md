# Sprint 1 completion report

**Completed:** 16 September 2026
**Scope:** stabilize authentication, resume uploads, and PDF extraction; redesign the existing pages; add regression coverage and local setup documentation.

## Outcome

Sprint 1 is complete for the local learning-project milestone. The application supports:

**Register → sign in → open the workspace → upload a text-based PDF → extract and save text → preview the result.**

The implementation is tested without creating records in the configured application database. The database was checked read-only and is already at revision `767a67c5e23e`.

## 1. Authentication

| Before | After |
|---|---|
| Malformed JWTs could trigger an invalid exception reference and return 500. | Missing, malformed, expired, missing-claim, invalid-subject, and missing-user tokens return 401. |
| Login password was an ordinary text input. | Password input is masked, labeled, and uses the correct autocomplete purpose. |
| Login failures triggered a full-page redirect. | Incorrect credentials remain on the form with the server's error message. |
| Registration returned no result to the caller and gave no next step. | The service returns the response; registration redirects to sign-in with a success message. |
| Passwords, JWTs, user objects, and resume responses were logged. | Those frontend logs have been removed. |
| Any restore failure removed the session. | Temporary network/server failures preserve the token and display a retry state. |
| A stale request could invalidate a newer session. | A 401 only clears the corresponding current token; restore results cannot replace a newer session. |
| The intended protected destination was ignored. | Sign-in returns to the protected route the user requested. |
| Concurrent duplicate email inserts could produce a server error. | The repository rolls back and returns a friendly conflict response. |

Additional changes:

- API response models explicitly expose public account fields.
- Registration and upload creation endpoints return HTTP 201.
- Authentication errors include the Bearer challenge header.
- Name/password validation is aligned between frontend and backend.
- New passwords use Argon2. Legacy bcrypt hashes can still be verified. Unrecognized stored values fail safely.
- Auth context definitions and the provider live in separate files, resolving the Fast Refresh lint error.

Key files: [token verification](../backend/app/core/get_current_user.py), [authentication routes](../backend/app/api/routes/auth.py), [API client](../frontend/src/api/axios.ts), [auth provider](../frontend/src/contexts/AuthContext.tsx), [login form](../frontend/src/components/auth/LoginForm.tsx), [registration form](../frontend/src/components/auth/RegisterForm.tsx).

## 2. Resume upload and extraction

- The service reads in 64 KiB chunks, rather than loading the entire file into a Python bytes object.
- Files larger than 5 MiB are rejected; partially written files are removed.
- The route runs synchronously in FastAPI's worker pool, keeping blocking file, PDF, and database work off the event loop.
- Filenames are normalized, length-checked, and stored separately from UUID-based disk filenames.
- Storage paths are absolute and resolve consistently from the backend directory.
- PDFs are opened with a context manager using the current `pymupdf` import.
- Empty, corrupt, encrypted, non-PDF, and textless files receive clear errors.
- Metadata and `raw_text` are inserted together in one database transaction.
- Persistence errors roll back the transaction and clean up the saved file during normal exception handling.
- The response schema now has active `from_attributes` configuration.
- Resume repository lookups require an owner ID.
- The TypeScript response type includes `raw_text`.
- The UI supports file browsing and drag-and-drop, shows loading/errors, resets stale results when a file changes, and provides a collapsible extracted-text preview.

The text preview is read-only and belongs to the current page session. Structured parsing, review editing, and persistent upload history remain later work.

Key files: [upload service](../backend/app/services/resume_service.py), [PDF service](../backend/app/services/pdf_service.py), [repository](../backend/app/repositories/resume_repository.py), [upload component](../frontend/src/components/ResumeUpload/ResumeUpload.tsx).

## 3. Interface redesign

The pages now share a responsive visual system: dark green navigation, a warm neutral workspace, restrained teal accents, consistent cards and spacing, and reusable SVG icons. Tailwind is imported correctly and shared CSS handles desktop/mobile layouts.

| Page | What changed |
|---|---|
| Home | Working navigation, a new hero and illustration, clear description of available features. |
| Login | Branded layout, masked password, accessible labels, inline validation and server feedback. |
| Register | Matching layout, password confirmation, aligned validation, success navigation. |
| Dashboard | Personalized greeting, upload action, workflow cards, honest roadmap links. |
| Resume | Drop zone, file validation, selected-file state, extraction feedback, text preview, upload guidance. |
| Profile | Displays the real signed-in account name and email; explains future resume-derived fields. |
| Jobs | Designed planned-feature state instead of an unexplained heading. |
| Applications | Designed planned-feature state with the intended future workflow. |
| Settings | Real sign-out action and clearly labeled planned preferences. |
| Not found | Useful return-to-workspace navigation. |

Navigation remains available on small screens through a horizontally scrollable menu, including Settings. Keyboard focus styles, a skip link, accessible form error associations, status announcements, and reduced-motion support were added. The page title and favicon now use JobPilot branding.

No fabricated job counts, match scores, applications, or resume statistics are shown.

Key files: [shared styles](../frontend/src/styles.css), [workspace layout](../frontend/src/layouts/MainLayout.tsx), [UI components](../frontend/src/components/ui), [pages](../frontend/src/pages).

## 4. Configuration, migrations, and documentation

- Fixed the extra `}` in the Docker PostgreSQL password value.
- Added backend, frontend, and Docker `.env.example` files without real credentials.
- CORS origins are configurable, with both local development hostnames allowed by default.
- Backend environment-file and upload paths no longer depend on where the process was launched.
- Online/offline Alembic modes consistently use the configured database URL; percent characters are escaped when passed through Alembic's configuration interpolation.
- Repaired the historical user migration to preserve credential values by renaming the column, and to backfill timestamps for existing rows.
- Named the resume foreign key explicitly, matching the previous PostgreSQL-generated name, so downgrade works for both old and new installations.
- Replaced deprecated `datetime.utcnow` calls while retaining the existing naive-UTC column convention; no new schema migration was introduced.
- Excluded uploaded PDFs from Git.
- Added a project-specific [setup and testing guide](../README.md), and replaced the frontend template README with relevant instructions.

**Existing data:** no migrations, account changes, or resume uploads were made against the configured application database. Historical migration corrections affect future execution of those revisions; do not replay already-applied revisions. Legacy password values are preserved, not automatically converted from an unknown format. See the README before upgrading an older populated database.

## 5. Verification

### Automated checks

| Check | Result |
|---|---|
| Backend application regression tests | **22 passed** |
| Frontend regression tests | **9 passed** |
| Isolated PostgreSQL 16 migration tests | **3 passed** |
| ESLint | **Passed** |
| TypeScript + Vite production build | **Passed** |
| Git whitespace/diff check | **Passed** |
| Offline upgrade and downgrade SQL generation | **Passed** |

**Total: 34 targeted tests passed.**

Backend coverage includes account creation, public response fields, password hashing, duplicate insert handling, login/restoration, token failures, upload ownership, file validation, PDF extraction, CORS, rollback, and cleanup after failures.

Frontend coverage includes bearer headers, incorrect-login behavior, protected-session expiry, temporary network failures, stale-request protection, registration payloads, validation, error messages, and password masking.

Migration coverage uses a separate disposable PostgreSQL container. It checks a fresh database round trip, a populated legacy user surviving upgrade/downgrade with credentials preserved, and downgrade compatibility with the original unnamed foreign key. The container was stopped and removed after testing.

Test files: [backend](../backend/tests/test_sprint1.py), [frontend](../frontend/tests/sprint1.test.cjs), [PostgreSQL migrations](../backend/tests/test_postgres_migrations.py).

The pre-existing Neon Coast game tests remain untouched and outside the JobPilot `npm test` command because their game source is missing. Dependency-level deprecation/experimental warnings remain in test output; none caused failures.

### Browser and live checks

- Checked real Home, Login, and Register views; submitting an empty login form showed field validation.
- Checked workspace layouts with temporary server-rendered sample-profile fixtures, not real user records.
- Inspected dashboard and upload designs, and checked all six workspace pages for horizontal overflow at desktop and 390 px mobile widths: none found.
- Removed temporary preview files/tabs and reset the viewport override afterward.
- Frontend `/login`: **HTTP 200**.
- Backend `/docs`: **HTTP 200**.
- Backend `/auth/me` with a malformed token: **HTTP 401** and a clear message.
- Configured database connection: **successful**, existing migration head `767a67c5e23e`.

Browser checks of protected-page fixtures verify layout, not a full browser-driven account/upload workflow. Authentication and upload behavior are covered by the isolated application tests.

## 6. What remains outside Sprint 1

1. Structured resume parsing.
2. Editable extraction review and saving confirmed profile fields.
3. Resume history and retrieval UI.
4. Job email ingestion and a job database.
5. Matching, AI assistance, tailoring, and application tracking/automation.
6. Password recovery, email verification, token refresh/revocation, and production deployment hardening.

Normal upload failures are cleaned up, but process crashes or an ambiguous commit failure may still require storage reconciliation. Production request/time limits and a background reconciliation worker are not part of this milestone.

## Next sprint

Build **raw text → structured resume draft**, keeping the original text separate from parsed fields. Add owner-scoped resume retrieval and parsing status, then implement editable review and confirmed-profile persistence in the following sprint.
