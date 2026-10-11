# OpenAI resume tailoring setup

## Enable the backend connection

1. Create an OpenAI API project and key using the [official quickstart](https://developers.openai.com/api/docs/quickstart).
2. Add these values to your local `backend/.env` (never commit the real key):

   ```dotenv
   OPENAI_API_KEY=your-secret-api-key
   OPENAI_MODEL=your-chosen-model-id
   ```

   Choose a model available to your API project that supports the Responses API and strict Structured Outputs. The model is intentionally not hard-coded. Check current model availability and API pricing before choosing. The app reports not configured until both values exist; it never substitutes a fake AI response.
3. From `backend/`, run `./venv/bin/python -m alembic upgrade head` and restart the backend.
4. Review/save a profile and a job containing its full description.
5. Open **Saved jobs → job → Tailor my resume**.
6. Check the disclosure and click **Generate with AI**. A separate draft is stored. Review the original profile, evidence, suggested changes, and questions. Edit as needed.
7. **Save draft edits**, or check the accuracy confirmation and **Approve resume**. Download the approved PDF, then return to the job to open its application website.
8. If you do not want the draft, choose **Discard draft** and confirm. This deletes the stored version and AI suggestions, including any unsaved edits in the editor. Your main profile and saved job remain. Approved or generating versions cannot be discarded.

## What is sent and stored

The backend sends reviewed profile experience, summary, education, skills and projects, plus the saved job's title/company/description/skills/location/work arrangement. Structured contact fields and project links are excluded. Personal information embedded in free-text descriptions can still be included. No browser cookies, Gmail credentials, API key, or ChatGPT history are sent as model input.

The API key authenticates only the server-side request to `https://api.openai.com/v1/responses`. `store=false` is set; this does not override the provider's separate logging/retention policies. No model tools, browsing, or automatic retries are enabled.

Versions store the source profile/job snapshots and revisions, original AI proposal/evidence, current user-edited content, model/prompt version, status and approval time. A UUID prevents a retry from creating another version for the same request. A recently generating version prevents overlapping generation for that account. Interrupted versions may remain generating; wait at least two minutes and start a new request. There is no background queue yet.

## Accuracy and approval

The model can select existing skills and entries and suggest rewritten bullets. Contact details, employers, job titles, dates, education, project technologies and links are copied from the source profile rather than rewritten by the model. Evidence references must exist; entry bullets must cite the same source entry; unsupported numeric claims are rejected.

These checks do not prove the meaning of a sentence is true. You must review semantic claims, responsibility, seniority and outcomes. Unknown experience should become a question, not an invented resume claim. Manual edits are your responsibility and apply only to this version.

Editing an approved version returns it to draft. Changing the main profile or job makes an older version stale and blocks approval/export; generate a new version. The PDF is selectable text in a simple A4 layout, with single-page fitting; oversized content must be shortened before approval.

## Troubleshooting

- **Not configured:** set both backend environment values and restart the backend.
- **Credentials rejected:** check the key and model access.
- **Usage limit:** check API billing/quota; wait before retrying.
- **Timeout or failed generation:** your main profile is unchanged. Refresh versions, inspect the failed version and start a new request. If the browser lost the response, retrying the same request finds the existing version.
- **Unsupported evidence/skill/number:** no usable draft is saved. Check the source and try a new version.
- **Missing description/profile:** save those first.

References: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [API authentication](https://developers.openai.com/api/reference/overview).

## Approved PDF folder

**Approve resume** now creates a PDF automatically in `backend/approved_resumes/<user_id>/job_<id>/version_<id>/revision_<n>/`, named from the profile first name and company, for example `amal_google_cv.pdf`. The page displays the relative location; downloads use that filename too. Draft saves do not create PDFs. Set `APPROVED_RESUME_DIR` to change the backend folder. This is a server-side folder (on your Mac during local development), not the browser Downloads folder.

Earlier approved PDFs remain independent archive copies even after later edits or deletion of database records. Each approval revision has its own folder. Existing approvals are not backfilled; approving again creates their file. No database migration is required. A process crash between writing a file and committing the database may leave an orphan archive file; normal caught commit failures remove the new file.

## In-app PDF preview

For an approved version, **View PDF** loads the authenticated PDF into an embedded viewer on the tailoring page. **Close PDF** hides it. Download and open-in-new-tab options remain available for browsers without embedded PDF support. Unsaved edits or a known stale version hide the preview and disable loading until the resume is eligible again. This is an approved PDF viewer; the pre-approval content preview remains unchanged.

## One-page tailoring update — 7 October 2026

AI is instructed to tailor every experience and project to the selected job using only that entry's verified facts, preserving its core contribution in concise bullets. Validation requires every source entry exactly once and disallows empty generated descriptions when the source has content. This checks coverage, not semantic completeness; review each rewritten claim. Prompt version: `tailoring-v2-all-entries-one-page`.

PDF generation tries compact A4 layouts with body text no smaller than 9.5pt. It returns one page or reports that the summary/bullets must be shortened; it never silently truncates or creates a second page. An oversized approval leaves the draft unapproved and writes no PDF. Previously archived files stay unchanged; generate a new version to apply the new AI instructions.

Validation: 15 tailoring backend tests passed, including missing-entry/description rejection, one-page text preservation, overflow rejection and approval rollback. A synthetic PDF was rendered and visually inspected. Live model quality has not been verified in this change.
