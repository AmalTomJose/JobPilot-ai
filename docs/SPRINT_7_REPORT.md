# Sprint 7 — AI-assisted resume tailoring

Updated: 6 October 2026

## Outcome

Saved job → Tailor my resume → explicit OpenAI request → separate draft → compare source/evidence → edit → approve → download PDF. The main profile stays unchanged. No automatic website fetching or application submission was added.

## Backend

- New `tailored_resumes` table and migration `d50a81c972eb` after `c49f70b861da`.
- `tailoring_ai.py`: OpenAI Responses API through existing HTTPX dependency; strict Pydantic JSON schema, fixed provider endpoint, 60-second timeout, no redirects/tools/automatic retries, safe error messages and `store=false`.
- `tailoring_service.py`: profile evidence IDs, selection of existing skills and mandatory coverage of every experience/project, citation and numeric checks, independent source snapshots, idempotent request IDs, short owner locks, revision conflict handling and explicit approval.
- `tailoring_pdf.py`: escaped text rendered through existing PyMuPDF into a selectable-text A4 PDF, single-page fitting with a readable minimum font size. No external resources or HTML supplied by the model are executed.
- Configuration: backend-only `OPENAI_API_KEY` and `OPENAI_MODEL`. Both are unset in the local environment; live generation remains disabled until configured.

### Routes

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/jobs/{job_id}/tailoring` | Setup/source readiness and paginated version summaries |
| POST | `/jobs/{job_id}/tailoring` | Consent and revision-checked generation of a separate draft |
| GET | `/jobs/{job_id}/tailoring/{version_id}` | Owned version, snapshots and stale status |
| PUT | `/jobs/{job_id}/tailoring/{version_id}` | Save edits or explicitly approve using expected revision |
| DELETE | `/jobs/{job_id}/tailoring/{version_id}?expected_revision=N` | Discard an owned draft or failed version with revision protection |
| GET | `/jobs/{job_id}/tailoring/{version_id}/pdf` | Export an approved, current version |

### Stored fields

`id`, `user_id`, `job_id`, `request_id`, `profile_revision`, `job_revision`, `revision`, `status`, `profile_snapshot`, `job_snapshot`, `data`, `proposal`, `section_order`, `model`, `prompt_version`, `error`, `created_at`, `approved_at`.

Statuses: generating → draft → approved; generation errors become failed. Editing approved content returns it to draft. Source changes make old versions stale. Foreign keys remove versions with deleted accounts/jobs.

## Frontend

- **Tailor my resume** on each saved job.
- Explicit data-sharing checkbox and generation button; setup and missing-input guidance.
- Version navigation; source profile/job snapshots; AI explanations, questions and per-statement evidence.
- Editable fields using the existing profile form, content preview and reorderable PDF sections.
- Accuracy confirmation before approval. PDF download is disabled for local unsaved changes and stale/unapproved versions.
- **Discard draft** asks for confirmation, deletes the unwanted version and its AI suggestions, and refreshes the version list. Approved and generating versions cannot be discarded.
- Saved job retains the application website link for the user to apply manually.

## Validation

- 187 backend tests passed, including 11 PostgreSQL migration/integration tests in an isolated disposable database.
- Discard follow-up: all 11 tailoring backend tests and 33 frontend tests passed; lint and production build passed. Tests cover ownership, revision conflicts, source preservation and protection of approved/generating versions.
- New tests cover ownership, explicit consent, missing setup/source, immutable main profile, idempotency, citation and numeric rejection, provider failures/refusals, stale versions, conflicting edits, approved-only PDF and multipage text preservation.
- New migration tested upgrade/downgrade, source record preservation and PostgreSQL owner-lock conflict; applied locally after tests passed.
- Sample PDF rendered and visually checked with synthetic data. Browser checks used a separate temporary database and mocked AI: generated a version, edited its summary, saved, required confirmation, approved, and displayed its PDF download link. Mobile-width layout was inspected. The PDF endpoint and returned file were verified; the in-app browser did not expose a completed file-download event, so a real Chrome download remains a manual check. Live OpenAI generation has not been tested because no key/model is configured.

## Practical limits

Evidence references and structured fields reduce mistakes; they do not prove every generated sentence is truthful. Manual approval is essential. There is no automatic factual entailment checker, external memory import, RAG, new AI matching score, or automatic application submission in this sprint.

Generation is synchronous. A crashed process may leave a generating record; the UI explains starting a new request after the two-minute overlap guard. Drafts persist in the database before approval; users can permanently discard draft or failed versions. Versions are also removed when their owning job/account is deleted. PDF export requires one readable page; oversized content blocks approval/export until shortened. The content preview is not a pixel-identical PDF viewer.

See [AI setup](AI_TAILORING_SETUP.md) for configuration and usage.

## Approved PDF storage follow-up

- Approval automatically writes a private PDF under `backend/approved_resumes`, separated by owner/job/version/revision. Filename: first name + company + `_cv.pdf`; unsafe characters are sanitized.
- Downloads use the same filename. The review page shows the stored relative path.
- Drafts create no PDF. Storage failure leaves approval unchanged; normal database commit failure cleans up the new file. Previous approved files remain independent archives.
- No migration or backfill. The optional `APPROVED_RESUME_DIR` setting controls the root folder; generated PDFs are ignored by Git.
- Validation: 13 tailoring backend tests, 33 frontend tests, lint and production build passed. Covers safe filenames, separate revision files, valid PDF bytes and storage-failure rollback.

## In-app PDF preview

For an approved version, **View PDF** loads the authenticated PDF into an embedded viewer on the tailoring page. **Close PDF** hides it. Download and open-in-new-tab options remain available for browsers without embedded PDF support. Unsaved edits or a known stale version hide the preview and disable loading until the resume is eligible again. This is an approved PDF viewer; the pre-approval content preview remains unchanged.

## One-page tailoring update — 7 October 2026

AI is instructed to tailor every experience and project to the selected job using only that entry's verified facts, preserving its core contribution in concise bullets. Validation requires every source entry exactly once and disallows empty generated descriptions when the source has content. This checks coverage, not semantic completeness; review each rewritten claim. Prompt version: `tailoring-v2-all-entries-one-page`.

PDF generation tries compact A4 layouts with body text no smaller than 9.5pt. It returns one page or reports that the summary/bullets must be shortened; it never silently truncates or creates a second page. An oversized approval leaves the draft unapproved and writes no PDF. Previously archived files stay unchanged; generate a new version to apply the new AI instructions.

Validation: 15 tailoring backend tests passed, including missing-entry/description rejection, one-page text preservation, overflow rejection and approval rollback. A synthetic PDF was rendered and visually inspected. Live model quality has not been verified in this change.
