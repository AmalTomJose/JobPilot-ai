# Sprint 5 — Explainable job matching

## Workflow

1. Upload a resume, build its draft, review it, and save a confirmed profile.
2. Add jobs manually or review pasted job-email drafts and save them.
3. Open **Matches** from the sidebar or Overview.
4. Choose **Find matches** to compare every saved (non-archived) job with the confirmed profile.
5. Review the skill coverage, matched skills, missing skills, and alias evidence.
6. Open a job or edit its skills. After changing a job or profile, run matching again.

**Refresh results** reloads saved results and detects outdated ones; **Find matches** performs a new calculation. Results also survive page reloads.

## How scoring works

Only the confirmed profile's top-level `skills` list and the saved job's `skills` list are compared. The matcher does not read raw resumes, unconfirmed drafts, titles, or descriptions to infer extra skills.

Skill names are Unicode-normalized, trimmed, compared without case distinctions, and mapped through a small ef alias dictionary. Examples include Postgres/PostgreSQL, React.js/React, and Microsoft SQL Server/MSSQL. Duplicate names and aliases count once.

`coverage = matched unique job skills / all unique job skills × 100`

Scores are rounded to one decimal place. Python and FastAPI against Python, FastAPI, and PostgreSQL produce 66.7%. Extra profile skills do not lower the score. Each match keeps both the original job skill name and the corresponding profile skill name for explanation.

Related technologies are not assumed equivalent: Java is not JavaScript, C is not C++, React is not React Native, and AWS EC2 is not the same label as general AWS expertise. Future alias changes must increment the matcher version.

With skills on both sides but no overlap, coverage is 0%. If either side has no skills, the score is null and the UI says **Not enough information**. Missing skills means absent from the confirmed list; it is not a claim that the person lacks the skill.

## Saved results and the new table

Migration `e05b3c742df6` follows `d94a2b631ce5` and adds `job_matches`.

| Field | Purpose |
| --- | --- |
| `id`, `user_id`, `job_id` | Result identity, owner, and saved job |
| `profile_id`, `profile_revision` | Exact confirmed profile version used |
| `job_revision` | Saved job version used |
| `matcher_version` | Matching rule version, initially `skill-coverage-v1` |
| `score` | Nullable coverage percentage |
| `matched_skills` | JSONB pairs of job/profile skill labels |
| `missing_skills` | JSONB list of unmatched job skill labels |
| `reason` | Why the result cannot be scored, when applicable |
| `computed_at` | Time of calculation |

There is one current snapshot per job, not an audit history. Re-running replaces that snapshot. Database constraints enforce one row per job, positive revisions, and scores between 0 and 100. Deleting a referenced job, profile, or account removes its matching snapshots through foreign keys.

Changing the profile identity/revision, job revision, or matcher version marks a saved result **Outdated** when results are read. The UI hides the old percentage and explicitly labels its breakdown as historical. New jobs are **Not checked**.

Current scored jobs rank first, descending by coverage, followed by current unscored jobs, outdated results, and unchecked jobs. Job ID breaks ties consistently. Results are paginated, 20 per UI page.

## Archived jobs

Archived jobs are excluded from the default view and all matching runs. **Show archived jobs** includes them for reference. To calculate or refresh an archived job's result, restore it to Saved in the job editor first.

## Backend structure

- `services/skill_matcher.py`: pure normalization, alias mapping, and scoring.
- `models/job_match.py`: SQLAlchemy result table.
- `repositories/match_repository.py`: owner-scoped queries and owner row locking.
- `services/match_service.py`: matching transactions, result persistence, sorting, pagination, and outdated-state detection.
- `schemas/job_match.py`: API response contracts.
- `api/routes/match.py`: authenticated endpoints.

Paths above are relative to `backend/app`.

| Endpoint | Purpose |
| --- | --- |
| `GET /matches?include_archived=false&limit=20&offset=0` | List owned jobs and their saved result states, plus pending/outdated counts and profile readiness |
| `POST /matches/run` | Calculate and persist all owned non-archived jobs; return processed/scored/insufficient counts |

No profile produces a 409 response with a clear setup instruction. The UI also guides users to add profile skills or save jobs when those prerequisites are missing.

Matching holds the same per-user `NOWAIT` row lock used by profile/job writes. A competing request receives a retryable 409. The entire matching run commits together; an error rolls back its changes. Reads never expose another account's jobs or results.

## Frontend changes

Added a lazy-loaded Matches page, matching API service, typed responses, and reusable result cards. Sidebar, breadcrumb, and Overview now link to Matches. The page includes loading, retry, error, empty, pending, insufficient-data, and outdated states. Dynamic imported text is rendered as text, not HTML.

## Validation

- 122 backend application tests passed.
- All 7 PostgreSQL integration tests passed in a disposable database, including the new migration's upgrade/downgrade, JSONB fields, lock conflicts, and preservation of existing jobs.
- 23 frontend tests passed; lint and production build passed.
- Total: **152 passing tests** across those runs.
- Browser verification used a synthetic account and separate API/frontend/database: matching, ranking, alias evidence, missing skills, archived filter, reload persistence, job editing, outdated detection, and recomputation passed.
- Phone (390 px) and desktop (1366 px) layouts were visually checked; neither had horizontal overflow.
- The migration was applied to the normal local database. `alembic check` reported no remaining model/schema differences. Existing app records were not rewritten.

## Limits and next step

This is transparent skill coverage, not AI matching or a hiring probability. It does not weight essential versus optional skills, years of experience, education, location, salary, or visa requirements. Skills buried only in prose or project descriptions must first be reviewed into the structured skill lists.

Matching is an explicit synchronous batch operation intended for this local learning project; a large production collection would need background processing. Another tab's changes are detected on refresh/navigation, not through live push notifications.

The next planned sprint can connect an email provider and automate the intake of job drafts. AI parsing remains deferred as requested.

No commit or push was performed; earlier uncommitted work was preserved.
