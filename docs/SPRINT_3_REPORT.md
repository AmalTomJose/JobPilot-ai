# Sprint 3 — Review and confirm your profile

## Outcome

You can now review a parsed resume, correct its fields, add or remove experience/education/project entries, and explicitly save a confirmed profile. Profile and Overview display that saved data. An open/close sidebar button is included on desktop and mobile.

No AI is used in this sprint. The parser rules from Sprint 2 remain unchanged.

## Try the workflow

1. Open **My resume** and select an uploaded resume.
2. Build its draft if needed, then choose **Review & confirm profile**.
3. Compare the form with **Original extracted text** and the parser notes. On smaller screens, **Compare original text** jumps to the source.
4. Correct the contact details, summary, skills, experience, education, and projects. Leave unknown values empty. Lists use one item per line; web links require `http://` or `https://`.
5. Check the confirmation box and choose **Save confirmed profile**.
6. The Profile page shows your saved details. **Edit profile** reopens those corrections.
7. Overview shows the confirmed summary and counts of skills, experience, education, and projects.
8. Use the menu button in the top bar to close/open the sidebar, or the close button inside it. Mobile starts closed, and selecting a navigation link closes it on mobile. The layout uses the freed space when collapsed.

One account has one current confirmed profile. Reviewing another resume starts from that resume's parsed draft and displays a replacement notice. Saving replaces the current profile's details, not the uploaded documents or parser output.

## Why another table?

There are three different representations of a resume:

| Table | Data | Who changes it |
|---|---|---|
| `resumes` | Original PDF metadata and extracted `raw_text` | Upload workflow |
| `resume_parses` | Rule-generated draft, warnings, parser version | Parser workflow |
| `profiles` | Human-reviewed contact, summary, skills, experience, education, projects | Explicit review save |

Keeping confirmed data separate means **Rebuild draft cannot erase your corrections**. Registration name/email also remain separate from professional contact details.

## New `profiles` columns

| Column | Meaning |
|---|---|
| `id` | Profile record ID |
| `user_id` | Owner; unique, so each account has one current profile |
| `source_resume_id` | Source resume; nullable if the source is later deleted |
| `source_parser_version` | Parser version used when this source was first confirmed |
| `revision` | Increases on each successful save; rejects stale browser edits |
| `data` | JSONB containing the reviewed fields and lists |
| `created_at` | First profile creation time |
| `updated_at` | Most recent successful save time |

The migration is `c83f1a520bd4`, after Sprint 2's `b72e0f419ac3`. It only adds the profile table. The unique owner and foreign key constraints enforce relationships. Deleting a source resume sets the reference to null while preserving confirmed details; deleting an account cascades to its profile.

The migration was tested on an isolated PostgreSQL database, then applied to the configured local JobPilot database. `alembic check` reported no schema drift. No real user profile or resume content was changed during testing.

## Backend request flow

```text
PUT /profile
  → authenticate current user and validate the request body
  → lock owner row (also protects the first save)
  → compare expected_revision with the saved revision
  → check source resume ownership
  → require a completed parse when first confirming or changing source
  → save independent profile JSON and increment revision
  → commit and return the profile
```

- `GET /profile` returns the current user's confirmed profile, or 404 if none exists.
- `PUT /profile` creates or updates it. The body contains `source_resume_id`, `expected_revision`, and `data`. Use revision 0 only for the first save.
- Missing/other users' source resumes return 404. Unauthenticated requests return 401.
- Invalid input returns 422. Stale revisions, overlapping saves, or missing completed drafts return 409.
- A profile already confirmed from a source remains editable even if a later re-parse fails. Its initial source parser version is retained.
- Database failures roll back. Concurrent writes use PostgreSQL row locks plus the revision comparison; a unique owner constraint provides a second safeguard.
- Extra fields such as `user_id`, parser `source_text`, and `unclassified_text` are rejected in the reviewed data. Ownership always comes from the login session.

The profile schema trims text and turns empty optional strings into null. It validates contact email and complete HTTP(S) links, rejects URL credentials, limits text/list lengths, and rejects an entirely empty profile. Optional details can remain unknown. Strings are rendered as text, not injected HTML; links are displayed as text.

## Frontend request flow

```text
Review & confirm profile
  → GET selected resume + saved parse + current profile
  → same source? load confirmed corrections; otherwise load parsed draft
  → convert null values and lists into editable form fields
  → user edits and confirms
  → convert fields back to profile data (without parser evidence)
  → PUT /profile with the expected revision
  → show saved profile
```

React Hook Form manages fields and repeatable entries. The confirmation checkbox is a UI requirement; submitting an authenticated PUT request is the API save action. No confirmation/audit history table is introduced.

The router now uses React Router's data-router setup so review pages can block navigation with unsaved edits. A modal offers keeping edits or discarding them. Browser refresh/close uses the browser's unload warning. Changes are not autosaved. Failed saves preserve the form. Conflicts offer an explicit discard-and-reload action, with a second confirmation before replacing unsaved fields.

Sidebar visibility is local to the mounted workspace. It stays consistent while navigating between workspace pages and resets to the screen-size default after a full reload. Hidden navigation is removed from keyboard access; the opener exposes its expanded state, and closing the sidebar returns focus to that button.

## Main files

- `backend/app/models/profile.py`: SQLAlchemy profile table mapping.
- `backend/app/schemas/profile.py`: validated reviewed-data contract.
- `backend/app/repositories/profile_repository.py`: owner lock and database operations.
- `backend/app/services/profile_service.py`: ownership, revision, provenance, and save transaction.
- `backend/app/api/routes/profile.py`: authenticated GET/PUT endpoints.
- `backend/alembic/versions/c83f1a520bd4_create_profiles.py`: additive migration.
- `frontend/src/pages/ResumeReview/ResumeReview.tsx`: loading, review, confirmation, conflicts, and navigation protection.
- `frontend/src/components/Profile/ProfileFields.tsx`: editable fields and repeatable entries.
- `frontend/src/components/Profile/profile-form.ts`: explicit conversion between form strings and stored profile data.
- `frontend/src/pages/Profile/Profile.tsx`: confirmed profile display.
- `frontend/src/components/Profile/ProfileSummary.tsx`: dashboard summary.
- `frontend/src/layouts/MainLayout.tsx`, `components/Sidebar/Sidebar.tsx`, and `components/Navbar/Navbar.tsx`: sidebar controls.

## Verification

- 57 backend application tests, including 11 new confirmed-profile tests.
- 5 PostgreSQL integration tests, including profile migration round trips, JSONB storage, first-save locking, stale revisions, and preservation of original text/drafts.
- 11 frontend tests, including 6 new tests for form conversion, source separation, API authentication/revisions, errors, and escaped rendering.
- Frontend ESLint and production build.
- Browser testing with a synthetic account in a disposable database: build draft, open review, edit name, remove/add experience, confirmation required, save, reload, reopen corrections, invalid-link validation, two-tab conflict, explicit conflict recovery, and preservation after rebuilding.
- Sidebar open/close checked on desktop and at 390px mobile width. Review inspected at desktop and mobile widths without horizontal page overflow.

The regular backend suite skips the five PostgreSQL tests unless `JOBPILOT_TEST_DATABASE_URL` is set. They were run separately on the disposable PostgreSQL database.

## Boundaries and next work

- One current profile per user; no profile version history, merge interface, or automatic import over saved corrections.
- No autosave. Browser warnings do not provide crash recovery or preserve edits after session expiry.
- Parser warnings describe extraction and remain visible even after corrections; they are not a review checklist whose items are automatically resolved.
- The Profile UI edits through its source resume. There is no source-deletion UI in this sprint; if the source is deleted externally, the confirmed data survives and can be updated through the API.
- Jobs/email ingestion, matching, AI tailoring, and application automation remain future sprints.
- Existing unrelated edits were preserved, including the removed icon/test files and a login debug log in `auth.service.ts`. That pre-existing log prints the submitted login data and should be removed before using real credentials.
- No Git commit was created.

The next sprint can add job ingestion and a job database, using this confirmed profile as the trusted input for later matching.
