# Resume parsing fixes — version 3

## Reported problems

Experience descriptions split incorrectly and the project section did not parse correctly. The supplied CV was read directly for verification, without saving it to the application database or copying it into the repository.

## Causes and fixes

- The PDF exports its bullet as U+F0B7, directly followed by text. Normalize this marker and support symbol bullets without a following space. Wrapped lines now stay within the same bullet.
- Add Associate, Executive, and Technician to recognized role terms. Associate roles can now begin their own experience entry.
- Tighten company-first entry detection so a sentence before the next role is not mistaken for a company name.
- Recognize Education and Training as an education heading. Support short training qualification headings; prevent education content from becoming another project.
- Extract a project name from the portion before a pipe separator when the entry has supporting bullets or technologies. Preserve the full heading in its source block.
- Preserve long, explicitly delimited skill lists instead of treating them as prose. Recognize Backend and Databases and Cloud and Tools category labels.
- Bump the resume parser to rules-v3 and the job parser to job-rules-v3 because job parsing shares the corrected skill-list helper.

## Verified result for the supplied CV

- Three experience entries, with 5, 2, and 1 joined description bullets respectively.
- One project entry, with its name and two joined description bullets.
- Two education/training entries with institutions and dates.
- Full skill names retained rather than shortened or omitted.

Project technologies remain empty when there is no explicitly labeled technology list; the technologies mentioned in the narrative remain visible in the project description. No new facts are invented.

## Validation and use

106 backend tests passed; 6 optional PostgreSQL tests were skipped. Two synthetic regression tests reproduce the relevant layout, role, bullet, heading, and skill-list patterns. No schema changes were needed.

Select the saved resume and use Rebuild draft. The fix operates on stored extracted text, so another PDF upload is not required for these specific issues. Confirmed profile data remains unchanged until explicitly reviewed and saved. If an existing confirmed profile loads previous corrections during review, those saved values are retained intentionally and can be edited.

No database records, original PDFs, commits, or pushes were changed by this fix.
