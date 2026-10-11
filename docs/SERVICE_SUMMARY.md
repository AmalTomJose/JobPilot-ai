# Service Summary

Backend quick reference · JobPilot AI · Updated 6 October 2026

**Scope:** all 22 Python modules currently in `backend/app/services`, including constructors, parser callbacks and nested helpers. This is a snapshot of the implemented code, not the future AI/RAG plan.

## Read this first

| Concept | Remember it as |
| --- | --- |
| Route | Receives the HTTP request and selects the service. |
| Schema | Validates input and defines response fields. |
| Service | Applies the application's rules and coordinates the task. |
| Repository / SQLAlchemy | Reads or changes database records. Some services use SQLAlchemy directly. |
| Parser | Converts text into fields; does not automatically save them. |
| Worker | Calls services in the background. |
| Commit | Makes a transaction's changes persistent. |
| Flush / stage | Sends or prepares changes within a transaction; not a final commit. |
| Rollback | Cancels that transaction's uncommitted changes. |
| Owner-scoped | Limits a query/action to the signed-in user's records. |

## Workflow memory aid

| Workflow | Main function chain |
| --- | --- |
| Account | `register()` → password hash → user; `login()` → credential check → access token |
| Resume upload | `upload_resume()` → `extract_text()` → `page_text()` → store PDF details and raw_text |
| Resume draft | `ResumeParseService.parse()` → `parse_resume()` → store parsing result |
| Profile | Review draft → `ProfileService.save()` → confirmed profile + new revision |
| Gmail discovery | `sync()` → `messages()` → `save_message()` → `message()` → `extract_message()` → `discover()` |
| Older imported emails | `backfill()` → read local email_messages → `discover()` |
| Description capture | `preview_capture()` → review → explicitly save job or `save_capture_draft()` |
| Approve discovery | Approval route → `JobService.create(candidate_id=...)` → save job + mark approved |
| Dismiss / restore | `set_status()` inside `mutation()` |
| Matching | `MatchService.run()` → `match_skills()` → store comparison; `list()` flags outdated results |
| Resume tailoring | `TailoringService.generate()` → `facts_for()` → `generate_proposal()` → `assemble()` → separate draft |
| Tailored PDF | User reviews → `TailoringService.save(approve=True)` → approved/current checks → `render_resume()` |

## Sync vs discover vs backfill vs approve

| Action | Purpose | What it does NOT do |
| --- | --- | --- |
| `sync()` | Retrieves selected Gmail emails and processes a batch. | Does not automatically approve jobs. |
| `discover()` | Creates individual candidate records from an email already supplied to it. | Does not visit job websites or invent missing descriptions. |
| `backfill()` | Applies discovery to older emails already in the database. | Does not download Gmail again or delete existing records. |
| `create(..., candidate_id=...)` | Saves the user's reviewed job and marks its discovery approved. | Does not submit a job application. |

**Backfill example:** you imported 20 emails before Discovered jobs existed. Clicking **Discover from existing emails** processes those stored emails and fills in missing discovery records. It handles up to 100 emails per request. `after_id` is the last processed email's database ID; `next_cursor` tells the frontend where to continue. Repeating it reuses existing discoveries and preserves dismissed/approved decisions. Existing saved jobs can be recognized as already approved.

## Service index

| File | Responsibility |
| --- | --- |
| [auth_service.py](../backend/app/services/auth_service.py) | Accounts and sign-in |
| [resume_service.py](../backend/app/services/resume_service.py) | PDF upload |
| [pdf_service.py](../backend/app/services/pdf_service.py) | PDF → plain text |
| [resume_parser.py](../backend/app/services/resume_parser.py) | Resume text → structured draft using rules |
| [resume_parse_service.py](../backend/app/services/resume_parse_service.py) | Run, reuse and store resume parsing |
| [profile_service.py](../backend/app/services/profile_service.py) | Human-confirmed resume information |
| [email_service.py](../backend/app/services/email_service.py) | Coordinate Gmail connection and ingestion |
| [gmail_client.py](../backend/app/services/gmail_client.py) | HTTP communication with Google |
| [email_text.py](../backend/app/services/email_text.py) | Encoded email/MIME/HTML → readable text |
| [email_candidates.py](../backend/app/services/email_candidates.py) | Identify individual openings in email content |
| [discovered_service.py](../backend/app/services/discovered_service.py) | Automatic collection; manual approval |
| [gmail_links.py](../backend/app/services/gmail_links.py) | Open the original Gmail message |
| [job_parser.py](../backend/app/services/job_parser.py) | Job text → structured fields using rules |
| [capture_service.py](../backend/app/services/capture_service.py) | Temporary job-description preview and explicit draft saving |
| [job_service.py](../backend/app/services/job_service.py) | Explicit drafts and saved jobs |
| [match_service.py](../backend/app/services/match_service.py) | Run, save and present profile/job comparisons |
| [skill_matcher.py](../backend/app/services/skill_matcher.py) | Explainable skill coverage calculation |
| [text_rules.py](../backend/app/services/text_rules.py) | Shared text and skill helpers |
| [job_sources.py](../backend/app/services/job_sources.py) | Source classification and explicit provider job IDs |
| [tailoring_ai.py](../backend/app/services/tailoring_ai.py) | Optional OpenAI request and validated structured proposal |
| [tailoring_service.py](../backend/app/services/tailoring_service.py) | Evidence, independent versions, editing and approval |
| [tailoring_pdf.py](../backend/app/services/tailoring_pdf.py) | Approved resume content → selectable-text PDF |

## 1. auth_service.py

**Purpose:** Accounts and sign-in. [Open source](../backend/app/services/auth_service.py)

| Function | What it does | Data / side effect |
| --- | --- | --- |
| `AuthService.__init__()` | Connects the service to UserRepository. | Setup only |
| `AuthService.register()` | Rejects duplicate emails, hashes the password and creates an account. | Writes users |
| `AuthService.login()` | Checks credentials and returns a JWT access token with basic user details. | Reads users; returns token |

## 2. resume_service.py

**Purpose:** PDF upload. [Open source](../backend/app/services/resume_service.py)

| Function | What it does | Data / side effect |
| --- | --- | --- |
| `ResumeService.__init__()` | Stores the repository and upload-folder location. | Setup only |
| `ResumeService.upload_resume()` | Checks PDF type/name and 5 MB size limit, saves a uniquely named file, extracts text and creates the resume record. Removes the file on failure. | Writes PDF and resumes |

## 3. pdf_service.py

**Purpose:** PDF → plain text. [Open source](../backend/app/services/pdf_service.py)

| Function | What it does | Data / side effect |
| --- | --- | --- |
| `PDFService.page_text()` | Reads positioned text lines, separates clear columns and orders them for reading. | No database write |
| `PDFService.page_text.render()` | Nested helper: sorts lines by position and preserves useful vertical gaps. | No database write |
| `PDFService.extract_text()` | Opens and validates the PDF, processes each page and joins the text. Rejects password-protected or unreadable/image-only input; does not perform OCR. | Reads PDF; returns raw text |

## 4. resume_parser.py

**Purpose:** Resume text → structured draft using rules. [Open source](../backend/app/services/resume_parser.py)

| Function | What it does | Data / side effect |
| --- | --- | --- |
| `normalize()` | Cleans Unicode, spaces and excessive blank lines in a working copy. | No database write |
| `split_sections()` | Recognizes headings such as Experience, Skills, Education and Projects; retains unclassified sections. | No database write |
| `labeled()` | Finds one unambiguous value from labels such as Company: or Degree:. | No database write |
| `links()` | Finds and deduplicates URLs. | No database write |
| `date_value()` | Finds an explicit duration or date near an entry heading, avoiding bullet achievements. | No database write |
| `role_line()` | Checks whether a line resembles a job title. | Returns true/false |
| `company_line()` | Checks whether a line could be a company heading rather than a role, date or description. | Returns true/false |
| `blocks()` | Groups lines into experience, education or project entries using entry headings. | No database write |
| `header_parts()` | Splits combined headings into parts and removes detected date text. | No database write |
| `descriptions()` | Collects bullet descriptions and joins continuation lines. | No database write |
| `parse_resume()` | Builds contact, summary, skills, experience, education and projects data. Keeps uncertain source text and returns warnings and parser version. | Returns ParseResult; does not save it |
| `parse_resume.warn()` | Nested helper: adds a structured parsing warning. | Updates the in-memory warning list |

## 5. resume_parse_service.py

**Purpose:** Run, reuse and store resume parsing. [Open source](../backend/app/services/resume_parse_service.py)

| Function | What it does | Data / side effect |
| --- | --- | --- |
| `ResumeParseService.__init__()` | Stores the parsing repository. | Setup only |
| `ResumeParseService.get()` | Checks resume ownership and retrieves its existing parse record. | Reads resumes and resume_parses |
| `ResumeParseService.parse()` | Locks the owned resume, validates text, reuses a matching completed parse unless forced, or runs the parser and stores draft/warnings/status/version. Saves a failure status if parsing fails. | Writes resume_parses; commits or rolls back |

## 6. profile_service.py

**Purpose:** Human-confirmed resume information. [Open source](../backend/app/services/profile_service.py)

| Function | What it does | Data / side effect |
| --- | --- | --- |
| `ProfileService.__init__()` | Stores the profile repository. | Setup only |
| `ProfileService.get()` | Returns the user's confirmed profile; reports not found when none exists. | Reads profiles |
| `ProfileService.save()` | Locks the owner, checks expected revision and source resume/parse, saves reviewed data and increases the profile revision. | Writes profiles |

## 7. email_service.py

**Purpose:** Coordinate Gmail connection and ingestion. [Open source](../backend/app/services/email_service.py)

| Function | What it does | Data / side effect |
| --- | --- | --- |
| `fingerprint()` | Creates a SHA-256 hash for values such as OAuth state and browser binding. | Returns hash; not encryption |
| `epoch()` | Converts a UTC datetime into integer seconds for Gmail date queries. | Returns timestamp |
| `EmailService.__init__()` | Stores the repository/database and Gmail client; allows a test client to be supplied. | Setup only |
| `EmailService.require_config()` | Rejects Gmail operations when required configuration is missing or invalid. | No database write |
| `EmailService.status()` | Returns public connection settings, sync status and whether another page remains. | Reads email_connections |
| `EmailService.start()` | Creates short-lived state/browser binding and an encrypted PKCE verifier, then returns the Google consent URL. | Writes email_connections |
| `EmailService.callback()` | Validates the one-time callback, exchanges the code, verifies mailbox/scope and stores the encrypted refresh token or connection error. | Calls Google; writes email_connections |
| `EmailService.active_connection()` | Checks configuration and obtains a locked, connected Gmail record. | Reads/locks email_connections |
| `EmailService.token()` | Decrypts the saved refresh token and obtains a temporary Google access token. | Calls Google; returns token |
| `EmailService.provider_failure()` | Records a provider error; marks reconnection required and clears scheduling when needed. | Changes the connection object; caller commits |
| `EmailService.labels()` | Fetches and sorts custom Gmail labels; records provider errors if necessary. | Calls Google; may write connection status |
| `EmailService.configure()` | Validates the selected custom label, stores date and auto-sync choice, resets changed scan settings and schedules the next run. | Calls Google; writes email_connections |
| `EmailService.disconnect()` | Attempts Google revocation, removes local credentials/settings and disables auto-sync while retaining imported records. | Calls Google; writes email_connections |
| `EmailService.save_message()` | Skips already-seen/deleted/unselected/too-old emails; fetches a new email, decodes its text and invokes discovery. Stores unsupported-body warnings. | Stages email_messages/discovered_jobs; sync commits |
| `EmailService.sync()` | Processes one batch, records counters and checkpoints, and schedules continuation. Provider failure rolls back the batch and records a failed run. | Calls Google; commits emails/discoveries/connection/run |

## 8. gmail_client.py

**Purpose:** HTTP communication with Google. [Open source](../backend/app/services/gmail_client.py)

| Function | What it does | Data / side effect |
| --- | --- | --- |
| `GmailError.__init__()` | Creates a readable provider error with reconnect, invalid-cursor and missing-message flags. | Error object only |
| `configured()` | Checks OAuth settings, encryption key and allowed callback/frontend URL configuration. | Returns true/false |
| `encrypt()` | Encrypts a secret with the configured Fernet key. | Returns encrypted text |
| `decrypt()` | Decrypts a stored secret; requests reconnection through GmailError if it cannot be opened. | Returns secret in memory |
| `GmailClient.request()` | Sends an HTTP request with timeout and response-size bounds; translates network/provider errors into sanitized GmailError messages. | Network request; no database write |
| `GmailClient.authorization_url()` | Builds the Google OAuth consent URL with read-only scope, state and PKCE challenge. | Builds URL only |
| `GmailClient.exchange()` | Exchanges the authorization code and verifier for Google tokens. | Calls Google |
| `GmailClient.refresh()` | Uses the refresh token to obtain a temporary access token. | Calls Google |
| `GmailClient.get()` | Helper for authenticated Gmail API GET requests. | Calls Google |
| `GmailClient.profile()` | Retrieves the connected mailbox identity. | Calls Google |
| `GmailClient.labels()` | Retrieves Gmail labels. | Calls Google |
| `GmailClient.messages()` | Lists up to ten matching message IDs using label/date filters and an optional page token. | Calls Google; does not fetch full bodies |
| `GmailClient.message()` | Fetches one email in full format using its Gmail message ID. | Calls Google |
| `GmailClient.revoke()` | Requests revocation of Google access. | Calls Google |

## 9. email_text.py

**Purpose:** Encoded email/MIME/HTML → readable text. [Open source](../backend/app/services/email_text.py)

| Function | What it does | Data / side effect |
| --- | --- | --- |
| `HTMLText.__init__()` | Initializes collected text, hidden-tag tracking and links. | Setup only |
| `HTMLText.handle_starttag()` | Adds line breaks, tracks links and ignores script/style/head content. | Builds text in memory |
| `HTMLText.handle_endtag()` | Closes hidden sections, adds safe link targets and paragraph breaks. | Builds text in memory |
| `HTMLText.handle_data()` | Collects visible text outside hidden sections. | Builds text in memory |
| `decode_body()` | Decodes base64url and the declared character encoding; rejects unreadable/oversized bodies and unsupported attachment downloads. | Returns text; no network request |
| `body_text()` | Walks nested MIME parts, prefers plain text over duplicate HTML alternatives, converts HTML and skips attachments. | Returns text; no database write |
| `extract_message()` | Builds the final readable text with subject, checking that content exists and stays within the size limit. | Returns source text or raises BodyError |

`BodyError` is a custom exception without locally defined methods. It reports unsupported/unreadable email content.

## 10. email_candidates.py

**Purpose:** Identify individual openings in email content. [Open source](../backend/app/services/email_candidates.py)

| Function | What it does | Data / side effect |
| --- | --- | --- |
| `job_link()` | Recognizes allowed direct job URLs, rejects unsafe/unrelated links and normalizes known providers. | Returns URL or None; never follows it |
| `Anchors.__init__()` | Initializes HTML anchor parsing state. | Setup only |
| `Anchors.handle_starttag()` | Starts collecting anchor targets while ignoring hidden sections. | In-memory parsing |
| `Anchors.handle_data()` | Collects visible anchor labels. | In-memory parsing |
| `Anchors.handle_endtag()` | Validates a completed link and records a conservative title when recognizable. | Builds Opening objects |
| `html_parts()` | Finds HTML bodies inside MIME parts, skipping attachments and excessive nesting. | Yields decoded HTML |
| `extract_openings()` | Combines HTML links with plaintext links, removes repeats and returns up to 50 individual openings. | Returns Opening list; no database/network write |

`Opening` is a data container with `title` and `job_url`; its constructor is generated by `@dataclass`. The parser never visits these links.

## 11. discovered_service.py

**Purpose:** Automatic collection; manual approval. [Open source](../backend/app/services/discovered_service.py)

| Function | What it does | Data / side effect |
| --- | --- | --- |
| `matching_discoveries()` | Finds owned openings for a URL, including older URL hashes using the same Naukri/Indeed job ID. Preserves previous decisions. | Owned database read |
| `identity()` | Normalizes provider/general URLs and hashes the result for per-owner opening deduplication. | Returns hash or None |
| `discover()` | Finds individual openings in a stored email and creates missing candidates. Replaces old pending linkless placeholders when real links become available. Leaves uncertain fields empty; recognizes already-saved jobs and preserves existing decisions. | Stages/flushed discovered_jobs; caller commits |
| `get()` | Retrieves one discovered opening belonging to the requesting user. | Owned database read |
| `listing()` | Returns a paginated list filtered by status and optional LinkedIn/Naukri/Indeed/Other source. | Owned database read |
| `mutation()` | Context manager: locks the owner, commits on success and rolls back/ translates errors on failure. | Transaction boundary |
| `set_status()` | Dismisses or restores a discovery. Rejects changing an already-approved discovery here. | Writes discovered_jobs |
| `backfill()` | Runs discovery for up to 100 already-stored emails after a cursor ID, preserving jobs/drafts and returning the next cursor. | Reads local emails; writes missing discoveries; no Gmail request |

## 12. gmail_links.py

**Purpose:** Open the original Gmail message. [Open source](../backend/app/services/gmail_links.py)

| Function | What it does | Data / side effect |
| --- | --- | --- |
| `original_email_url()` | Builds a fixed Gmail URL using mailbox and Message-ID header; falls back to a best-effort direct message route for older records. | Builds URL only; no network/database write |

## 13. job_parser.py

**Purpose:** Job text → structured fields using rules. [Open source](../backend/app/services/job_parser.py)

| Function | What it does | Data / side effect |
| --- | --- | --- |
| `canonical_url()` | Normalizes URL host/default ports/query order and removes known tracking parameters and selected anchors. | Returns comparable URL |
| `heading_candidate()` | Recognizes a conservative title/company heading such as Developer at Example. | Returns title/company pair or None |
| `parse_job_email()` | Extracts job fields and skills from supplied text. Detects ambiguity/multiple roles and returns review warnings; also used for captured descriptions. | Returns JobParseResult; no database/network write |
| `parse_job_email.warn()` | Nested helper: adds a warning without duplicates. | Updates in-memory warnings |

## 14. capture_service.py

**Purpose:** Temporary job-description preview and explicit draft saving. [Open source](../backend/app/services/capture_service.py)

| Function | What it does | Data / side effect |
| --- | --- | --- |
| `preview_capture()` | Parses supplied description text, preserves the full description, applies provided title/company/URL and adjusts warnings. | Returns temporary preview; no database write |
| `save_capture_draft()` | Locks owner and explicitly saves reviewed capture fields/source as a browser draft. Identical source and edits reuse the existing draft. | Writes job_imports; commits or rolls back |

## 15. job_service.py

**Purpose:** Explicit drafts and saved jobs. [Open source](../backend/app/services/job_service.py)

| Function | What it does | Data / side effect |
| --- | --- | --- |
| `url_fingerprint()` | Hashes the canonical application URL. | Returns hash or None |
| `JobService.__init__()` | Stores the job repository. | Setup only |
| `JobService.duplicate_info()` | Builds a readable duplicate-job explanation and linkable job identity. | Returns DuplicateJob |
| `JobService.import_response()` | Builds a draft response and checks whether a matching job is already saved. | Reads duplicate information |
| `JobService.get_import()` | Retrieves a draft belonging to the user and returns its review response. | Reads job_imports |
| `JobService.detail()` | Builds saved-job detail, including its original draft when one is linked. | Reads optional source draft |
| `JobService.get()` | Retrieves one saved job after checking ownership. | Reads jobs |
| `JobService.handle_error()` | Rolls back and translates uniqueness/lock conflicts into useful errors; re-raises other errors. | Rollback/error handling |
| `JobService.import_email()` | Parses explicitly pasted email text and creates/reuses a draft. Can refresh an unsaved older-parser draft. | Writes job_imports |
| `JobService.check_duplicate()` | Checks existing URL/source-import identity and raises a conflict when a duplicate exists. | Reads jobs |
| `JobService.create()` | Locks owner, validates source/discovery state and duplicates, saves reviewed job fields and marks matching discoveries approved in the same transaction. | Writes jobs and possibly discovered_jobs |
| `JobService.update()` | Checks ownership and expected revision, prevents duplicate URL/source conflicts, saves edits and increments revision. | Writes jobs |

## 16. match_service.py

**Purpose:** Run, save and present profile/job comparisons. [Open source](../backend/app/services/match_service.py)

| Function | What it does | Data / side effect |
| --- | --- | --- |
| `MatchService.__init__()` | Stores the matching repository. | Setup only |
| `MatchService.run()` | Requires a confirmed profile, locks owner, compares skills against saved non-archived jobs, and stores results with profile/job revisions and matcher version. | Writes job_matches |
| `MatchService.list()` | Lists results in useful order and marks each pending/current/outdated based on revisions and matcher version. | Reads matches/jobs/profile; does not recompute |

## 17. skill_matcher.py

**Purpose:** Explainable skill coverage calculation. [Open source](../backend/app/services/skill_matcher.py)

| Function | What it does | Data / side effect |
| --- | --- | --- |
| `skill_key()` | Normalizes spelling/case/spacing and applies explicit aliases such as postgres → postgresql. | Returns normalized skill |
| `skill_map()` | Deduplicates normalized skills while keeping their display names. | Returns mapping |
| `match_skills()` | Compares profile and job skills, returns matched/missing skills and percentage coverage. Missing input skills produce no score, not zero. | Pure calculation; no database write |

**Example:** profile has Python + SQL; job asks for Python + SQL + Docker → 2/3 = **66.7% skill coverage**. This is not a hiring probability.

## 18. text_rules.py

**Purpose:** Shared text and skill helpers. [Open source](../backend/app/services/text_rules.py)

| Function | What it does | Data / side effect |
| --- | --- | --- |
| `normalize_text()` | Standardizes Unicode, line endings and certain invisible/bullet characters in the parsing copy. | Returns cleaned text; original source is unchanged |
| `unique()` | Removes blanks and case-insensitive repeats while preserving order. | Returns list |
| `mentioned_skills()` | Finds explicitly named technologies from the known-skills list using word boundaries. | Returns skills; does not infer skills |
| `skill_values()` | Splits skill lists, removes category headings and extracts named technologies from prose-like requirements. | Returns deduplicated skills |

## Database memory aid

| Table | Meaning |
| --- | --- |
| users | Login accounts; password hashes rather than raw passwords. |
| resumes | Uploaded PDF metadata/path and extracted raw_text. |
| resume_parses | Machine-extracted resume draft, status, version and warnings. |
| profiles | Human-confirmed profile and its revision. |
| email_connections | Gmail credentials, chosen label/date and sync checkpoints/schedule. |
| email_messages | Imported source emails and message-ID duplicate tracking. |
| email_sync_runs | Batch history, processed/review/skipped counters and errors. |
| discovered_jobs | Possible openings; pending, dismissed or approved, with source email and approved job link. |
| job_imports | Explicitly saved drafts plus older Gmail-created drafts. |
| jobs | Human-approved/manual saved jobs and revisions. |
| job_matches | Stored skill comparisons and versions used to calculate them. |

## Important distinctions

| Easy to confuse | Actual difference |
| --- | --- |
| PDF extraction vs resume parsing | Extraction reads words from a PDF; parsing assigns those words to fields. |
| Parser vs parsing service | Parser computes a result; service handles ownership, reuse, status and persistence. |
| Resume parse vs profile | Parse is a machine draft; profile is your confirmed information. |
| Discovery vs draft vs saved job | Discovery is a possible opening; draft is an explicitly stored review; saved job is approved. |
| EmailService vs GmailClient | Service manages application workflow; client performs Google HTTP calls. |
| Message ID vs job URL | Message ID identifies an email; normalized job URL helps identify an opening across emails. |
| Hash vs encryption | Hash is a one-way comparison value; encrypted credentials can be decrypted with the key. |
| Profile/job revision vs parser/matcher version | Revisions track saved data edits; versions identify processing rules. |
| Original email vs full JD | Email may contain only a summary/link. Full job descriptions must be supplied separately when absent. |
| “Open original email” | Builds a Gmail link; the browser opens it only when clicked. It may show a matching search result first. |

## Related background runner (outside the services folder)

Source: [gmail_worker.py](../backend/app/workers/gmail_worker.py)

| Function | Purpose |
| --- | --- |
| `tick()` | Finds connected, opted-in accounts whose sync is due and calls `EmailService.sync(automatic=True)`. |
| `main()` | Runs a check every 30 seconds, or one check with `--once`. It must be started separately. |

Normal Gmail scheduling: another page remains → five minutes; scan finished → fifteen minutes; provider failures → increasing retry delay. The 30-second worker check reads the schedule; it does not fetch every mailbox every 30 seconds.

## Current boundaries

- Resume/job parsing and skill matching still use rules. Optional OpenAI resume tailoring is implemented separately and requires backend configuration. RAG retrieval, agent search and application automation remain future work.
- Gmail sync creates discoveries, not automatic editable drafts. Manual email paste and browser Save for later explicitly create drafts.
- Source email bodies are still retained. Backfill does not clean them up.
- URL deduplication is not semantic duplicate detection; different URLs can describe the same job.
- The PDF reader does not provide OCR for scanned resumes.
- Standalone capture previews do not save database rows until an explicit save.

**Memory sentence:** Extractors get text. Parsers organize it. Matching compares it. AI proposes a tailored version. You review and approve it. PDF export renders the approved version. Services and the database keep the sources and versions separate.

## 19. job_sources.py

**Purpose:** Recognize source websites without network requests.

| Function | What it does | Data / side effect |
| --- | --- | --- |
| `source_site()` | Classifies a safe website hostname as LinkedIn, Naukri, Indeed or Other. | Returns source label; no network |
| `provider_job_id()` | Reads explicit IDs from supported Naukri job-listings (including /jd/ email links) and Indeed jk links to recognize the same opening across URL variations. | Returns provider/ID pair or None |

## 20. tailoring_ai.py

**Purpose:** Server-side OpenAI connection for optional, explicitly requested resume tailoring.

| Function | What it does | Data / side effect |
| --- | --- | --- |
| `configured()` | Checks that a backend key and model are present. | Returns boolean; never exposes the key |
| `generate_proposal()` | Sends bounded profile facts and job context to OpenAI with a strict output schema; handles provider errors/refusals/timeouts. | External API call; returns validated proposal; no direct DB write |

## 21. tailoring_service.py

**Purpose:** Separate resume versions grounded in the reviewed profile, with manual approval.

| Function | What it does | Data / side effect |
| --- | --- | --- |
| `facts_for()` / nested `walk()` | Builds source fact IDs while excluding contact fields and links. | Returns evidence dictionary |
| `validate_order()` | Requires each of five supported resume sections exactly once. | Raises validation error |
| `assemble()` / nested `statement()` | Validates evidence, entry references, existing skills and numeric claims, then builds a draft with unchanged identity fields. | Returns profile-shaped draft; cannot establish semantic truth |
| `TailoringService.__init__()` | Binds the database session and job repository. | Setup only |
| `source()` | Retrieves the owned job and current profile. | Owned database reads |
| `get()` | Retrieves a version scoped by owner and job. | Owned database read |
| `response()` | Adds whether source revisions changed to the version response. | Reads current profile/job |
| `listing()` | Returns setup readiness and ten version summaries at a time. | Owned database read |
| `generate()` | Checks consent/revisions/readiness, creates an idempotent generating version, releases the lock, calls AI and stores a draft or failure. | Writes version snapshots and proposal; never changes main profile |
| `save()` | Saves edits or explicitly approves with owner locking and optimistic revision checks. Edits revoke previous approval. | Writes only the selected resume version |
| `discard()` | Checks ownership and expected revision, then permanently removes a draft or failed version. Rejects approved or generating versions; preserves the profile and job. | Deletes one tailored_resumes row |

## 22. tailoring_pdf.py

**Purpose:** Export approved resume content as selectable PDF text.

| Function | What it does | Data / side effect |
| --- | --- | --- |
| `render_resume()` | Builds an escaped, local A4 layout in the selected order, tries compact single-page layouts and rejects overflow. Approval is enforced by the route before calling it. | Returns PDF bytes in memory |
| nested `text()` | Escapes all user/model text for the internal HTML layout. | No scripts or external resources |
| nested `line()` | Joins nonempty factual fields for headings/contact details. | Returns escaped text |
| nested `bullets()` | Turns description items into escaped bullet markup. | Returns internal layout markup |

## 23. Approved resume file storage

**Source:** `backend/app/services/tailoring_storage.py`

| Function | What it does | Effect |
| --- | --- | --- |
| `resume_filename()` | Uses the profile first name and company to create a safe filename such as `amal_google_cv.pdf`. Missing values use resume/company. | No write |
| `resume_filename.slug()` | Converts text to lowercase ASCII and removes path characters. | No write |
| `approval_path()` | Separates PDFs by owner, job, version and revision beneath APPROVED_RESUME_DIR. | Computes private path |
| `store_approved_pdf()` | Renders the approved content and exclusively writes a private PDF. Never overwrites an earlier approval. | Writes PDF on approval only |

`TailoringService.save()` writes the PDF before committing approval. Storage failure rolls back approval; a failed database commit removes the newly written file. These files are independent approval archives: later edits, discarding a returned-to-draft version, or deleting database records do not remove earlier approved PDFs. They are excluded from Git and are not publicly served.

## One-page tailoring update — 7 October 2026

AI is instructed to tailor every experience and project to the selected job using only that entry's verified facts, preserving its core contribution in concise bullets. Validation requires every source entry exactly once and disallows empty generated descriptions when the source has content. This checks coverage, not semantic completeness; review each rewritten claim. Prompt version: `tailoring-v2-all-entries-one-page`.

PDF generation tries compact A4 layouts with body text no smaller than 9.5pt. It returns one page or reports that the summary/bullets must be shortened; it never silently truncates or creates a second page. An oversized approval leaves the draft unapproved and writes no PDF. Previously archived files stay unchanged; generate a new version to apply the new AI instructions.

Validation: 15 tailoring backend tests passed, including missing-entry/description rejection, one-page text preservation, overflow rejection and approval rollback. A synthetic PDF was rendered and visually inspected. Live model quality has not been verified in this change.
