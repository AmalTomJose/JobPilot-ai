# Browser extension: click → preview → send

## What is implemented

1. Open an individual job from a Gmail email card or any permitted job page.
2. Click the JobPilot Chrome extension.
3. Inspect/edit the title, company, URL, and full description in the popup.
4. Confirm that you reviewed the content and the site permits importing it.
5. Click **Send to JobPilot**. A new JobPilot tab opens.
6. Sign in if necessary, then choose **Receive and extract preview**.
7. Review extracted fields. Choose:
   - **Add to jobs**: saves a confirmed job without creating a draft row.
   - **Save for later**: explicitly stores the reviewed fields as a draft.
   - **Cancel**: discards the temporary review after the leave confirmation.

The extension does not automatically click Apply or submit applications. No AI model receives content.

## Install locally in Chrome

The unpacked extension is in the repository's `extension/` directory.

1. Start JobPilot's frontend at **http://localhost:5173** and backend at its configured API address.
2. In Chrome, open **chrome://extensions**.
3. Enable **Developer mode**.
4. Click **Load unpacked**.
5. Select `/Users/amaltomjose/jobpilot-ai/extension`.
6. Pin **JobPilot — Preview a job** using Chrome's extensions menu.

The extension is a local development build, not a Chrome Web Store publication. Review its files/permissions before loading it. No account password or API key is required in the extension.

After code updates, use **Reload** on its card in chrome://extensions. Frontend sign-in and extension use must occur in the same Chrome profile. The extension currently targets **localhost:5173 exactly**; 127.0.0.1, other ports, and hosted deployments need deliberate configuration changes in the extension and matching sender validation.

Apply the database migration from `backend/`:

```sh
./venv/bin/python -m alembic upgrade head
```

## How page reading works

- It runs only when you open the extension popup, using temporary `activeTab` permission.
- Selected text takes priority. Select just the description if automatic detection does not work.
- Otherwise it looks for one structured `JobPosting` or one recognized description section.
- It never falls back to copying the entire page.
- It accepts one description between 40 and 20,000 characters.
- Title and company can remain empty and be corrected later.
- Popup values and extracted text are displayed as text, not executable website markup.
- LinkedIn extraction is deliberately disabled; use manual copy/paste for LinkedIn. Other sites' permissions must also be respected. This is not a universal scraper.

Manual fallback: **Job inbox → Import job page**, or the **Paste description** link below an email opening. Enter the original URL and full text, then choose **Extract temporary preview**.

## Temporary storage and authentication

Before Send, content exists only in the extension popup. Closing it discards that preview.

After Send, the content is held in Chrome's session storage for at most ten minutes (expired items are cleaned on an alarm or subsequent activity). It is not sync storage or a database draft. Closing the destination tab removes its pending handoff, and restarting the browser clears session storage.

Only a random handoff nonce and extension ID appear in the destination URL fragment; the description and credentials do not appear in that URL. The receiving page must match the fixed origin, path, destination tab ID, top-level frame, nonce, and expiry. A successful claim consumes the record once.

The extension never receives the JobPilot login token. The signed-in web app uses its ordinary authenticated backend requests. Preview parsing does not insert database rows. Review data stays in React memory; closing/reloading after receipt loses it. A failed extraction request retains the received text in the page so it can be retried.

The extension declares `activeTab`, `scripting`, `storage`, and `alarms`. It has no persistent host permissions, cookies/history permission, remote code, or network fetch implementation. Alarms only clean expired handoffs.

## Email integration

Email summaries now expose distinct direct job links derived from stored MIME HTML, even when the original body extraction preferred plain text. Repeated links are collapsed; navigation links are ignored. Existing emails receive cards without modifying their stored content.

Gmail now collects individual openings in Discovered jobs for manual approval; neither single-job emails nor digests automatically create editable drafts. Original source emails and existing drafts are preserved. Manual email paste and standalone browser Save for later remain explicit draft actions. Saving a job with the same normalized URL marks its discovery approved. See [the current Sprint 6 report](SPRINT_6_REPORT.md).

Supported link recognition includes direct LinkedIn job links, Greenhouse/Lever job-page URLs, and conservative public job/career/position paths. Reading these URLs does not contact those providers. Tracking redirect wrappers and unsupported URL formats can require opening the original email manually. At most 50 distinct links are shown per email.

## Database changes

Browser capture migration `a27d5e964fb8` is part of Sprint 6:
- Adds `job_imports.source_type`, backfilling earlier imports as `email`.
- Allows `browser` as a saved job source.
- Adds no preview table. A later Sprint 6 migration, `b38e6fa750c9`, adds the separate `discovered_jobs` table.

Explicit browser drafts retain their edits and original capture text. Repeated identical draft-save requests reuse the same row; changed content produces a separate draft. Saving jobs preserves existing URL duplicate checks and owner scoping. Downgrade retains jobs and maps browser sources to the older source categories.

The incomplete Greenhouse/Lever API fetcher and description worker from the stopped implementation were removed. Discovery is now implemented separately without provider fetching. This workflow uses no provider API fetching.

## Validation and remaining manual check

Automated tests cover no-write previews, explicit draft/job saves, duplicate handling, ownership, URL/input validation, HTML link extraction, extension permission shape, page extraction fallbacks, handoff origin/tab/expiry validation, and one-time consumption.

Tests simulate Chrome extension APIs. Installing the unpacked extension and verifying an actual Chrome permission grant/handoff remains a manual check; unit tests are not a substitute for that browser integration check.

References:
- [Chrome activeTab](https://developer.chrome.com/docs/extensions/develop/concepts/activeTab)
- [Chrome external messaging](https://developer.chrome.com/docs/extensions/develop/concepts/messaging)
- [LinkedIn extension restrictions](https://www.linkedin.com/help/linkedin/answer/a1341387/prohibited-software-and-extensions)

### Earlier browser-capture verification

For the current discovery update and latest validation totals, see [Sprint 6 report](SPRINT_6_REPORT.md).

- Backend discovery: 153 application tests passed; 9 opt-in PostgreSQL tests skipped in ordinary discovery.
- All 9 PostgreSQL migration/integration tests passed separately in a disposable container.
- 29 frontend tests and 7 extension tests passed.
- Frontend lint and production build passed.
- Browser checks with synthetic data verified temporary extraction, Save for later, saving the reviewed draft as a browser-sourced job, and discarding a second preview without creating a job/draft.
- Applied migration `a27d5e964fb8` to the configured local database after integration tests.
- Actual unpacked-extension installation and the live Chrome handoff remain unverified; the extension API tests use mocks.


### Source views

Use **Job discovery → LinkedIn / Naukri / Indeed / Other sources** to review individual openings. Open the website, paste or receive a permitted extension preview, then review and approve. If the URL changed, choose the original opening in **Attach to a discovered opening** before saving. Approved and dismissed openings remain out of Pending when recognized on later imports. Gmail messages are not deleted.
