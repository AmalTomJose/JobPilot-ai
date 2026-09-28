# Sprint 4 — Job intake and inbox

Historical sprint report. The later [extraction v2 update](EXTRACTION_V2_REPORT.md) expands parser formats and allows refreshing older unsaved imports; see that report for current behavior.

## What changed

You can now build a private job database in two ways:

1. **Add a job:** enter fields, confirm review, and save.
2. **Paste a job email:** store the original text, extract a draft, review and correct it, confirm, and save.

The job inbox supports search, source/work-mode/status filters, pagination, and reopening pending imports. Saved jobs have detail and edit pages, original-email disclosure, and saved/archived status. Forms warn before discarding edits. Conflicting edits from older tabs return a conflict instead of overwriting newer changes.

The sidebar and navigation now expose Job inbox. Job pages use the shared responsive design and load separately to keep the initial bundle smaller. The login service no longer logs submitted credentials.

## Why two tables?

`job_imports` preserves what came in and what the parser originally extracted. `jobs` holds the values you reviewed and chose to save. Editing a job never rewrites the original email or extraction draft.

| Table | Fields and purpose |
| --- | --- |
| `job_imports` | `id`, `user_id`: identity and owner |
| | `raw_text`: exact original pasted text |
| | `source_hash`: SHA-256 of that text, unique per owner to reuse identical imports |
| | `draft_data`, `warnings`: extracted JSON and review notes |
| | `parser_version`, `created_at`: extraction provenance |
| `jobs` | `id`, `user_id`: identity and owner |
| | `source_import_id`, `source_type`: optional original import and manual/email origin |
| | `title`, `company`, `location`, `work_mode`, `employment_type`: reviewed basics |
| | `description`, `skills`, `application_url`: reviewed job content |
| | `url_hash`: normalized URL fingerprint for owner-specific duplicate detection |
| | `status`: saved or archived |
| | `revision`: starts at 1; increases on edits to reject stale updates |
| | `created_at`, `updated_at`: timestamps |

PostgreSQL stores JSON fields as JSONB. Database constraints enforce allowed statuses/work modes, positive revisions, one saved job per import, and unique URL fingerprints per owner. Manual jobs have no source import.

Migration `d94a2b631ce5` follows `c83f1a520bd4`. It adds the two tables and their constraints/indexes. It has been applied to the local development database; Alembic reported no remaining model/schema differences. Existing resume and profile data was not rewritten.

## How email text becomes a draft

The parser in `backend/app/services/job_parser.py` is a pure function: text goes in; structured fields, warnings, and parser version come out. It does not call AI or fetch URLs.

It recognizes explicit English labels such as `Job title:`, `Company:`, `Location:`, `Skills:`, `Apply:`, and `Description:`. Description sections collect following lines. Skills are split and deduplicated. Explicit application links take priority; a single unlabelled link is offered with a warning to check it. Missing, ambiguous, or unsupported values stay empty. Multiple distinct job titles cause an empty draft with a warning to paste one opening at a time.

For example, `Job title: Backend Developer` becomes `title: "Backend Developer"`, while an email without a company label leaves `company` empty. The original string remains unchanged in `raw_text`.

The intake service stores the parser result as an immutable import. The review form copies draft values into editable form state. Saving sends only reviewed job fields and the import ID. It does not replace `raw_text` or `draft_data`.

## Duplicate detection and access

- Every endpoint requires authentication and scopes reads/writes to the signed-in owner.
- Identical pasted text reuses its existing import, including its stored parser version.
- A source import can produce only one saved job.
- Matching normalized application URLs return a conflict with a link to the existing job, including archived jobs.
- URL normalization removes known tracking parameters and common apply/top anchors, normalizes the host/default port, and preserves meaningful hash routes and repeated query-value order. The original URL is retained for display.
- Jobs without URLs are not deduplicated by title or company; those values can legitimately repeat.
- Owner row locks and database uniqueness constraints protect concurrent saves. Edit requests must include the current revision.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/jobs` | Search/filter/paginate owned jobs |
| POST | `/jobs` | Save reviewed manual/imported fields |
| GET | `/jobs/imports` | Paginate unsaved imports |
| POST | `/jobs/imports` | Store original email and extract draft; reuse identical input |
| GET | `/jobs/imports/{id}` | Retrieve owned source/draft for review |
| GET | `/jobs/{id}` | Retrieve saved job and optional original import |
| PUT | `/jobs/{id}` | Update reviewed fields/status with expected revision |

## Code guide

- Backend `schemas/job.py` validates request/response fields and URLs.
- Backend `models/job.py` defines tables; `repositories/job_repository.py` handles owner-scoped database operations.
- Backend `services/job_service.py` coordinates extraction, duplicate detection, transactions, and revision checks.
- Backend `api/routes/job.py` exposes authenticated HTTP endpoints.
- Frontend `services/job.service.ts` calls the API; `types/job.types.ts` defines shared data shapes.
- Frontend `pages/Jobs` contains inbox, intake, review loading, and saved detail pages.
- Frontend `components/Jobs/JobEditor.tsx` supplies the shared review/edit form; `job-form.ts` converts between form strings and API values.

Paths above are relative to `backend/app` or `frontend/src` as indicated.

## Validation

- 82 backend application tests passed in final discovery; the 6 optional PostgreSQL tests were skipped in that ordinary run.
- All 6 PostgreSQL integration tests passed separately against a disposable database, including upgrade/downgrade, JSONB, lock conflicts, duplicate constraints, and preservation of earlier data.
- 17 frontend tests passed; lint and production build passed.
- Total: **105 passing tests** across those runs.
- Browser checks against an isolated synthetic account covered extraction, pending-import reload/reopen, review confirmation, unsaved-change warning, saving corrections while preserving source text, duplicate URLs, manual entry, search, archiving, source/work-mode filters, and repeated-email detection.
- A final dedicated mobile viewport inspection was not completed after the temporary browser services stopped. Responsive CSS is included, but automated/module checks do not prove every mobile layout.

## Current limits and next work

This sprint supports pasted plain text for one opening at a time. It does not connect to Gmail/Outlook, parse arbitrary HTML email, fetch application pages, match profiles, use AI, tailor resumes, or submit applications. Extraction remains deliberately conservative and requires human review.

Pending imports cannot currently be deleted/dismissed or reparsed through the UI. Unsaved corrections stay in memory; there is no autosave or offline recovery. Identical imports retain their original extraction version. Duplicate detection is based on source identity or normalized URL, not fuzzy job similarity.

The next development step is explainable matching between the confirmed profile and saved jobs, with visible matched/missing skills and clear handling of incomplete job data.

Sprint 4 changes are left uncommitted for the user to review and commit. No push was performed.
