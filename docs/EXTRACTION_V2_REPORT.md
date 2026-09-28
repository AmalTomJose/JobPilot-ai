# Extraction and parsing improvements — September 25, 2026

## Scope

Improved both resume and job-email extraction before starting job matching. These changes extend the existing local, deterministic parsers. They do not add AI, mailbox access, OCR, or external requests. No database migration is required for this update.

## PDF text extraction

Previously, PDF extraction followed the PDF's internal drawing order. That order can differ from the visible reading order.

The extractor now reads positioned text lines, orders them visually, and separates clear two-column layouts. Full-width lines divide columns into reading bands. Right-aligned dates are kept with the main content rather than being treated as a separate prose column. Blank lines reflect larger vertical gaps.

Image-only pages now produce an explicit error, including when other pages contain readable text, instead of silently returning only the readable pages. OCR is still required before uploading scanned documents. Complex layouts and PDFs with broken font mappings remain limitations.

## Resume parser: `rules-v2`

- Recognizes additional section aliases and inline headings, such as `Career Objective: ...` and `Technical Skills: ...`.
- Normalizes Unicode presentation characters, nonbreaking spaces, zero-width characters, and line endings in the parsing copy.
- Recognizes a plausible first-line name when a single valid contact email supports the header context; adds a review warning.
- Finds unlabelled phone numbers and handles contact fields separated by pipes; excludes date lines and numeric URLs.
- Supports common role/company headers separated by pipes, en dashes, or `at`, plus company-first entries.
- Recognizes month abbreviations, inline date ranges, and `to` separators while preserving the extracted date text.
- Keeps wrapped bullet continuations together and avoids splitting an entry merely because there is a blank line.
- Supports university-first education entries and more degree abbreviations.
- Recognizes short project headings when supported by a technology list or bullets.
- Keeps project technologies within the project rather than leaking them into the resume-wide skills section.
- Applies uncertain-column handling per section instead of disabling most parsing for the entire resume.

Original `raw_text` stays separate from the structured draft. Unsupported source blocks remain available for review. Titles, employers, or other fields that cannot be safely identified remain empty.

## Job-email parser: `job-rules-v2`

- Supports additional labels, Markdown emphasis, common bullet prefixes, and values on the line after a label.
- Recognizes explicit role/company relationships such as `Backend Developer at Example Labs` and `Example Labs is hiring a Backend Developer`, including common subject prefixes.
- Detects multiple distinct roles in those headings and refuses to combine them into one job.
- Reads sections such as About the role, Qualifications, Requirements, and Responsibilities.
- Keeps unlabeled email prose as a reviewable description instead of discarding it.
- Recognizes work mode within an explicit location such as `Bengaluru (Hybrid)`; conflicting modes stay empty.
- Recognizes standalone employment types such as Full-time.
- Extracts explicitly named technologies from description text using a small vocabulary, with a review warning. Lines containing negation or optionality are conservatively skipped; this is not a full language-understanding system.
- Prioritizes labeled application links and copied Markdown Apply links over unrelated URLs. Multiple unqualified links still require review.
- Stops description collection at common email footers.

No URL is fetched and no email text is sent to an external service. The pasted original is preserved exactly; normalization happens only in the parser's working copy.

## Using the improvements on existing documents

### Resume

- If the existing extracted text looks correct, select **Rebuild draft** to use the latest resume parser.
- If the text itself is out of order or incomplete, **upload the PDF again**, then build its draft. Existing stored text is not silently replaced.
- Rebuilding a draft does not overwrite the separately confirmed profile. Review and save deliberately.

### Job email

- Paste the content and choose **Extract & review**.
- Pasting the exact same unsaved email again refreshes an older-version draft, retaining the import ID and original text.
- An import attached to a saved job keeps its original extraction version and source data. Edit the saved job to correct its reviewed fields.
- Unsaved edits open in another browser tab are not synchronized or autosaved.

The resume and email screens now explain these actions.

## Validation

- **104 backend tests passed**, including 22 additional regression tests for these changes.
- **17 frontend tests passed**; frontend lint and production build passed.
- Ordinary backend discovery ran 110 tests with 6 optional PostgreSQL integration tests skipped. Those database tests were not rerun for this parser-only update.
- Synthetic PDFs test reordered content streams, two-column layouts, right-aligned dates, and mixed text/image-only pages.
- Resume/email cases cover realistic formats, ambiguous contact information, missing employers, multiple jobs, negated skill mentions, Unicode, source preservation, and old-version import refresh behavior.
- No real account data was changed during testing. These examples establish specific regressions, not an accuracy percentage across arbitrary real-world documents.

## Main implementation files

- `backend/app/services/pdf_service.py`: positioned PDF text extraction.
- `backend/app/services/resume_parser.py`: resume section/entry/contact rules.
- `backend/app/services/job_parser.py`: job-email recognition and review warnings.
- `backend/app/services/text_rules.py`: shared normalization and skill helpers.
- `backend/app/services/job_service.py`: controlled refresh of unsaved older imports.
- `backend/tests/test_extraction_quality.py`: synthetic layout and parser regressions.

## Remaining limitations

The rules target common English resume and email formats. Arbitrary HTML email, scanned images, severely interleaved columns, arbitrary prose relationships, and newsletters containing several jobs still need additional handling. Names inferred from a header and skills recognized from prose must be reviewed. The skill vocabulary is intentionally finite; explicit skill lists can retain names outside that vocabulary.

No commits or pushes were made. Existing Sprint 4 work was retained.
