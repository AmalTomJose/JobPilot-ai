# Sprint 2 — Resume parsing

## What is implemented

An uploaded resume can now produce a saved, structured draft. Its original `raw_text` is unchanged. The frontend can list saved uploads, retrieve a selected document, build its draft, show warnings and source blocks, and reopen it after a refresh.

Editing and confirming extracted fields remains Sprint 3. This sprint adds a read-only viewer, not an editable review page or a confirmed professional profile.

## Data contract

`parse_resume(raw_text: str) -> ParseResult` is independent of FastAPI and SQLAlchemy. It returns a Pydantic-validated draft, structured warnings, and `parser_version="rules-v1"`.

The draft contains:

- **Contact:** name, email, phone, location, links.
- **Summary:** the text under a recognized summary heading.
- **Skills:** deduplicated strings, preserving punctuation such as `C++`, `C#`, `Node.js`, and `CI/CD`.
- **Experience:** title, company, location, original date wording, description lines, source block.
- **Education:** institution, degree, explicit field of study, date wording, source block.
- **Projects:** explicit name, descriptions, technologies, links, source block.
- **Unclassified text:** header and unsupported sections retained for later review.

Unknown single values are `null`; empty collections are `[]`. Entry source blocks are normalized working copies. The full original extraction remains unchanged on the `Resume` record and is available separately in the UI.

## Rules and deliberate limitations

The parser normalizes line endings, nonbreaking spaces, and repeated blank lines. It detects whole-line section headings using English aliases, rather than treating any sentence containing “experience” as a heading.

Supported patterns include common title/company/date lines, pipe-separated job headers, degree/institution/date lines, and explicitly labeled fields. Blank lines before job bullets are handled without creating a second job. Recognized job descriptions may use bullets or plain text after the date line.

The parser deliberately avoids aggressive guesses:

- Names require `Name:` or `Full name:`. An unlabeled name stays empty and produces a warning.
- Phone/location fields require explicit labels; date ranges are not treated as phone numbers.
- Multiple header email addresses produce a warning instead of choosing a primary one.
- Project names and education fields of study need explicit labels.
- Unusual dates are retained in the source block or copied verbatim from an explicit date field, not converted into invented dates.
- Suspected column spacing produces a layout warning and suppresses potentially misleading entry/skill inference. Detection is heuristic; the parser cannot reconstruct arbitrary column layouts.
- Unknown sections and ambiguous entries remain available as source text.
- Empty text is rejected; input above 200,000 characters is rejected rather than silently truncated.

No AI service, network lookup, or external document processing is used.

## Persistence and lifecycle

New SQLAlchemy model: `ResumeParse`. New migration: `b72e0f419ac3`, following `767a67c5e23e`.

The table stores one current result per resume with a unique `resume_id`, JSONB `draft_data`, JSONB warnings, status, parser version, a SHA-256 fingerprint of the source, an optional failure message, and timestamps. The foreign key uses `ON DELETE CASCADE`.

A completed parse is reused only when its source fingerprint and parser version match. `force=true` explicitly replaces the current draft. A failed parse can be retried. This is not a history of every parser run.

The parser is synchronous. `processing` exists during the transaction; clients normally observe a committed `completed` or `failed` result. No background queue or polling worker is claimed. The parent resume row is locked with PostgreSQL `FOR UPDATE NOWAIT`, including the first parse before a draft record exists. A simultaneous request receives 409. The unique constraint provides an additional database safeguard.

Parser exceptions save a generic failure result without exposing internal exception details or personal text. Database failures roll back the transaction. A process crash releases the lock and rolls back, rather than leaving a separately committed processing state.

## API

All endpoints require authentication and scope access to the current user. Missing and other users’ records return 404.

| Method | Endpoint | Behavior |
|---|---|---|
| GET | `/resume?limit=50&offset=0` | Paginated owned upload summaries; excludes raw text and disk paths. Maximum limit is 100. |
| GET | `/resume/{resume_id}` | Owned document metadata and original raw text; excludes disk path. |
| POST | `/resume/{resume_id}/parse` | Reuses or creates a structured draft. |
| POST | `/resume/{resume_id}/parse?force=true` | Rebuilds the current draft. |
| GET | `/resume/{resume_id}/parse` | Returns the saved result; 404 when not yet parsed. |

Successful parse operations return HTTP 200 with the result. A saved parser failure also returns the result with `status="failed"`, `draft_data=null`, and a retry message. Clients must inspect `status`. Invalid source text returns 422, oversized text 413, and an overlapping parse 409.

## Frontend

**My resume → Your saved resumes → select a file → Build draft.**

The page retains the selected ID in `?id=...`, retrieves a saved draft on reload, offers explicit rebuilding, and presents all six sections alongside warnings and expandable source text. Selecting another document prevents a delayed response from showing the previous document’s draft. History/loading errors have retry actions. Untrusted resume strings are rendered as text; extracted links are not executed or injected as HTML.

The selector shows the latest 50 documents. Older records remain available through the paginated API or an owned resume ID in the page URL.

## Verification

- 14 deterministic parser tests using synthetic standard, ambiguous, and column-layout samples.
- 10 isolated API/service tests: ownership, persistence, retrieval, caching, forced rebuild, version/source invalidation, failure/retry, invalid inputs, and transaction rollback.
- 22 existing backend regression tests.
- 4 PostgreSQL integration tests, including JSONB storage, migration round trips, preservation of existing resume text, and simultaneous-request rejection.
- 5 frontend tests covering API requests and draft-panel behavior.
- Frontend production build and ESLint checks.
- Browser verification using a synthetic account in an isolated PostgreSQL database: login, saved-resume selection, Build draft, reload/reopen, and Rebuild draft. No user document was parsed for testing.
- Desktop and mobile overflow checks on the draft page.

The additive migration was applied to the configured local application database after isolated migration tests passed. Existing resume content was not rewritten. Temporary test services and the disposable PostgreSQL container are removed after verification.

The pre-existing deletions of `frontend/public/icons.svg` and `frontend/tests/sprint1.test.cjs` were left untouched. No commit was created for Sprint 2.

## Files to read first

1. `backend/app/schemas/resume_parse.py` — input/output structure.
2. `backend/app/services/resume_parser.py` — normalization and extraction rules.
3. `backend/app/models/resume_parse.py` — stored result.
4. `backend/app/services/resume_parse_service.py` — ownership, lock, cache, retries, and persistence.
5. `backend/app/api/routes/resume.py` — HTTP boundary.
6. `frontend/src/components/ResumeUpload/ResumeDraftPanel.tsx` — saved-document and draft UI.
7. `backend/tests/fixtures/resumes/` — synthetic inputs to learn from and extend.

## Next sprint

Add editable extraction review and a separate confirmed-profile save operation. Keep user-confirmed data separate from parser output so rebuilding a draft cannot overwrite corrections.
