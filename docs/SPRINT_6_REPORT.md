# Sprint 6 — Gmail discovery and manual approval

Updated: 2 October 2026. Gmail ingestion, multi-job discovery, and browser-assisted description capture belong to Sprint 6. This report describes the current implementation and replaces the earlier automatic Gmail-draft workflow.

## Workflow

**Connect Gmail → select a label/date → sync → discover individual openings → review → approve or dismiss.**

1. Gmail sync reads selected emails in bounded batches and stores the source email.
2. Direct job links become separate records in **Discovered jobs**. Six recognized openings produce six candidates, not one combined draft.
3. A single-job email can supply initial extracted fields. A multi-job digest supplies only the title/link for each opening; unknown company, skills, and description stay empty.
4. Open **Job inbox → Discovered jobs → Review**. Check the original website and correct the fields. **Add and extract full description** uses the existing paste-and-preview workflow.
5. **Approve and add to jobs** creates a saved job and marks the discovery approved in the same transaction.
6. **Dismiss** removes an opening from the pending queue. **Restore** returns it. Repeated emails do not reset these decisions.
7. Only saved jobs enter the existing matching workflow. No application is submitted.

A “candidate” means a possible job opportunity, not an applicant. The UI calls them **Discovered jobs**.

## What changed from the original Sprint 6 implementation

- Gmail no longer creates `job_imports` automatically, including for single-job emails.
- Added persistent, owner-scoped discovered openings with pending/dismissed/approved states.
- Added separate review, approve, dismiss, restore, and paginated list actions.
- Added **Discover from existing emails**. This explicitly processes stored emails in batches of 100, reuses discoveries, and preserves existing drafts and jobs. Migration alone does not run this conversion.
- Jobs already saved with a matching source import or normalized URL are recognized during discovery.
- Saving a matching job through the extension/manual capture also marks its discovered opening approved. Matching uses the normalized original URL; a completely different redirect URL may need review through the discovery itself.
- Existing manual **Paste job email** still explicitly creates a draft. Standalone browser captures can still use **Save for later**. These are user actions, not automatic Gmail draft creation.

## Storage: what each table means

| Table | Purpose and important fields |
| --- | --- |
| `email_connections` | One Gmail connection per owner; mailbox, encrypted refresh token, connection status, hashed OAuth state/browser binding, selected label/date, `auto_sync`, `next_sync_at`, page token, failure count |
| `email_messages` | Source email and Gmail duplicate tracking: owner + mailbox + Gmail message ID, subject/sender/date, original MIME payload, decoded `raw_text`, warnings; legacy `import_id` remains for existing drafts |
| `email_sync_runs` | Batch timestamps, status, processed-email/review/skipped counts, sanitized errors; the existing `imported` column now counts processed emails, not drafts or individual candidates |
| `discovered_jobs` | Unapproved opportunities: owner, first source email ID, normalized URL identity hash, original URL, extracted fields (reviewed fields after approval), source text, parser version/warnings, created date, pending/dismissed/approved status, approved job ID |
| `job_imports` | Explicitly saved drafts and older Gmail-created drafts; `source_type` distinguishes email/browser |
| `jobs` | Human-approved opportunities used for matching; reviewed title/company/description/skills, source, URL fingerprint, status and revision |

**Source email bodies are still retained.** This change separates discovery from approval; it does not implement email-body expiry, metadata-only storage, Gmail history IDs, RAG indexing, or deletion of older imports. Original source text remains available as evidence. Duplicate URLs keep the first discovery/source; this version does not store a many-to-many history of every email mentioning that job.

### Migrations

1. `f16c4d853ea7` — Gmail connections, messages, and sync runs; follows `e05b3c742df6`.
2. `a27d5e964fb8` — browser source on drafts/jobs; follows `f16c4d853ea7`.
3. `b38e6fa750c9` — `discovered_jobs`, owner/identity uniqueness, status constraint and queue index; follows `a27d5e964fb8`.

The discovery migration adds a table without changing existing jobs/drafts/emails. Downgrading it removes discoveries, but retains saved jobs and source emails.

## Duplicate handling

- Email identity: owner + mailbox + Gmail message ID prevents reimporting the same message.
- Opening identity: normalized job URL, including provider-specific direct-link normalization and removal of known tracking parameters. It deduplicates across emails for the same owner.
- Without a URL: the source email ID identifies the candidate. The app does not guess that two unrelated URL-less emails are the same opening.
- Dismissed/approved records remain as decision history. Repeated discovery leaves their state unchanged.
- Existing saved-job duplicate checks remain active. Approval and matching discovery updates use the owner row lock and commit together.

Different URLs can still refer to the same job. Semantic/AI deduplication is not implemented.

## Backend structure

- `app/api/routes/email.py`: authenticated Gmail connection, labels, settings, sync, history and disconnect; validated public OAuth callback.
- `app/services/gmail_client.py`: fixed Google endpoints, timeouts/response limits, PKCE, refresh/revoke and sanitized errors.
- `app/services/email_service.py`: connection lifecycle, page transactions, scheduling and invoking discovery.
- `app/services/email_text.py`: bounded MIME decoding and HTML-to-text extraction.
- `app/services/email_candidates.py`: direct opening-link recognition; no website fetching.
- `app/services/discovered_service.py`: opening creation, identity normalization, owned queries, dismissal/restoration and existing-email backfill.
- `app/services/job_service.py`: transactional manual approval and saved-job duplicate handling.
- `app/services/capture_service.py`: temporary rule-based extraction and explicitly saved browser drafts.
- `app/workers/gmail_worker.py`: independently running opt-in worker.

### Gmail routes (`/email/gmail`)

| Method/path | Action |
| --- | --- |
| GET / | Configuration and connection status |
| POST /connect | Start short-lived browser-bound Google consent |
| GET /callback | Validate state/cookie and exchange OAuth code |
| GET /labels | List custom labels |
| PUT /selection | Save label, UTC start date and auto-sync choice |
| POST /sync | Process one bounded batch |
| GET /messages | Paginated source-email summaries and opening links |
| GET /runs | Latest ten batch results |
| DELETE / | Revoke/remove connection; retain imported records |

### Discovery routes (`/jobs/discovered`)

| Method/path | Action |
| --- | --- |
| GET / | Filter by pending/dismissed/approved, with pagination |
| POST /backfill?after_id=… | Discover from up to 100 stored emails; return continuation cursor |
| GET /{id} | Owned discovery fields and source evidence |
| PATCH /{id} | Dismiss or restore; approved records cannot be reset here |
| POST /{id}/approve | Validate reviewed fields, create saved job and mark approved atomically |

Reading the list/detail does not create drafts or approve anything.

## Automatic syncing and security

- The worker checks the database every 30 seconds for opted-in, connected accounts whose sync time is due.
- Each Gmail request batch reads up to ten emails in the selected label/date window.
- Next batch: five minutes if pages remain; fifteen minutes after completing a scan. Provider failures back off up to six hours; revoked access requires reconnection.
- This is polling, not Gmail push/history-based synchronization. Existing message IDs prevent duplicates during rescans.
- The connection row is locked for a sync; each page commits as a unit. Provider failure rolls back source messages, discoveries and cursor movement together.
- Refresh tokens and PKCE verifiers are Fernet-encrypted. OAuth state/browser values are hashed, expire, and are consumed once. Access tokens are transient. Credential fields are omitted from responses; callback query logging is redacted.
- Sync does not mark emails read, delete mail, send mail or apply for jobs.

## Browser-assisted description capture

**Open job → click extension → preview → send → receive in JobPilot → review → save.**

The extension reads the active page only when clicked, using limited permissions. It does not receive the JobPilot login token. Its one-time handoff is bound to the expected app origin, destination tab, nonce and expiry. Standalone previews are temporary; a job or draft is saved only on an explicit action.

LinkedIn uses manual copy/paste. There is no Greenhouse/Lever API fetcher or automatic website crawling. Direct provider URLs can be recognized as links without contacting those APIs. See [browser capture setup](BROWSER_CAPTURE.md).

## Frontend and how to try it

1. **Settings → Gmail job alerts → Sync now** (or run the opted-in worker).
2. **Job inbox → Discovered jobs**.
3. For earlier imports, choose **Discover from existing emails** once; repeating it is safe.
4. Use **Review**, inspect the source, add the description if needed, confirm the checkbox, then **Approve and add to jobs**.
5. Check the **Approved** filter or **Saved jobs**. Use **Dismissed → Restore** to reconsider an opening.

Email sync summaries now say “emails processed” instead of “drafts”. Existing jobs, drafts, login accounts, resumes, profiles and matching data are preserved.

## Boundaries and future AI work

- Parsing is still rule-based; no AI model, vector database, RAG retrieval or agent ranking is added in this update.
- Full descriptions are not invented or fetched automatically. Digest candidates remain incomplete until supplied through permitted page capture/manual paste.
- Unsupported redirect links may not be discovered. Emails with multiple roles but no usable individual links receive a warning rather than a combined candidate.
- Recognition is bounded to 50 direct openings per email.
- A useful next AI stage can retrieve stored descriptions/profile evidence and rank candidates, with clear separation between extracted facts and suggestions. Approval remains a separate user action.
- Live Chrome extension permission/handoff and real Google consent are outside the mocked tests; this update does not claim those have been verified.

## Validation

- **171 backend tests passed**, including **10 PostgreSQL migration/integration tests** against a disposable local container (161 application tests). The focused discovery tests passed again after the final reviewed-field display adjustment.
- **30 frontend tests** and **7 extension tests passed**. Extension tests use mocked Chrome APIs.
- Frontend lint and production build passed. The existing approximately 501 kB main-bundle warning remains non-blocking.
- Browser verification used synthetic Gmail messages and a separate temporary SQLite database: two openings from one digest, dismiss/restore, review, full-description paste/extraction, explicit approval, saved-job fields, and separation of approved and pending queues.
- Migration tests covered fresh upgrade/downgrade, preservation of existing jobs, JSONB storage, approval locking, and retryable dismissal conflicts.
- Applied `b38e6fa750c9` to the configured local database after the isolated migration tests. Existing source emails/drafts were not deleted or automatically backfilled.
- No real Gmail fetch, provider website/API request, Chrome extension installation, or application submission was performed in this update. The Gmail worker was not started.

To repeat backend tests, use `./venv/bin/python -m unittest discover -s tests` from `backend/`. PostgreSQL cases require `JOBPILOT_TEST_DATABASE_URL` pointing to a disposable loopback database named `jobpilot_test`; never point that setting at your working database.


## Follow-up: open the original Gmail message

Discovered-job cards, pending discovery review pages, and imported-email cards now include **Open original email in Gmail ↗**. It opens a new tab and leaves the JobPilot review in place. The link uses the source mailbox as an account hint; sign in to that Gmail account if asked.

When the stored email includes a Message-ID header, the link opens Gmail search for that exact identifier, including archived/trash/spam locations. Gmail may show a matching conversation/search result first; click it to read the message. Older messages without that header use a best-effort direct Gmail message link. Gmail's UI routing is not a guaranteed public API; deleted messages or the wrong signed-in account may not open.

Links are generated from existing stored identifiers, with URL encoding and a fixed Gmail destination. No token is placed in the URL, no Gmail API request is made, and no database migration or new permission is needed. Discoveries link to their first stored source email. Owner scoping still applies.

Reference: [Google's documented Message-ID search operator](https://support.google.com/mail/answer/7190?hl=en).

Follow-up validation: 10 discovery tests and 23 Gmail tests passed; frontend lint and production build passed. Checks cover encoded mailbox/Message-ID links, legacy fallback, list/detail/history responses and existing owner isolation. Actual navigation inside the user's signed-in Gmail account was not exercised.


## Follow-up: separate source views (2 October 2026)

- Sidebar **Job discovery** contains All sources, LinkedIn, Naukri, Indeed and Other sources. Each view supports pending, approved and dismissed status filters, with server-side pagination/counts and owner scoping.
- Classification follows the individual opening's website, not the email sender. Approved jobs remain in Saved jobs and the approved discovery view.
- Workflow: Sync now → source view → Go to website (new tab) → paste a description or receive the existing extension preview → review → approve and save. Original Gmail messages remain accessible in a separate tab.
- Capture previews can be attached to a discovered opening explicitly when a website changes the URL. Matching original URLs are associated automatically. Nothing is approved merely by opening a page or extracting text.
- Recognizes direct Naukri job-listings URLs with 12-digit IDs and supported Indeed links with a 16-character jk ID. Tracking variants with the same supported provider ID retain existing decisions. Unsupported redirects/search links still require opening the email and manually importing an individual job.
- Migration `c49f70b861da` adds indexed source_site classification and fills existing rows without changing their status, identity, or job link. Applied to the local database after migration tests passed.
- Validation: 176 backend tests passed, including 10 disposable PostgreSQL migration/integration tests; 31 frontend tests passed; frontend lint and production build passed. Existing main-bundle size warning remains. This follow-up did not verify live Gmail or an installed Chrome extension.
- At the user's request, local testing data was cleared: 4 saved jobs, 4 matches, 23 discoveries, 44 imported emails, 40 drafts and 9 sync runs. Gmail messages, credentials, accounts, resumes and profiles were preserved. Sync cursors reset and automatic syncing paused, allowing a fresh manual Sync now with the existing label/date selection.

### Multi-job email link correction

Actual imported emails used LinkedIn `/comm/jobs/view/ID/` and Naukri `/jd/job-listings-...-ID` links, which the initial direct-link parser missed. Both email URL formats are now recognized without visiting websites. Repeated logo/title/action links resolve to one opening. Pending linkless placeholders from the old parser are replaced when individual openings are found; approved/dismissed decisions remain preserved. Existing stored emails were reprocessed into 39 openings (21 LinkedIn, 17 Naukri, 1 Indeed). No Gmail messages were changed and no jobs were automatically approved.

Regression coverage includes a mixed-provider digest, repeated links, excluded search links, placeholder replacement, and repeat-discovery deduplication. Backend suite: 177 tests, with 10 opt-in PostgreSQL tests skipped for this parser-only update.


### Email review navigation

Removed **Add and extract full description** from the email discovery review. **Go to website** is the primary action for obtaining the full description. Users can send an extension preview or copy from the website and use **Saved jobs → Import job page**, selecting the discovered opening before saving. No automatic fetching was added.
