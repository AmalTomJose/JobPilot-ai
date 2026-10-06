from hashlib import sha256
import json
from app.models.job import JobImport
from app.schemas.capture import CapturePreview
from app.services.job_parser import parse_job_email
from app.services.job_service import JobService


def preview_capture(capture):
    result = parse_job_email(capture.description)
    # Preserve the entire description, including sections the rule parser misses.
    result.draft_data.description = capture.description
    result.draft_data.application_url = capture.url
    if capture.title:
        result.draft_data.title = capture.title
    if capture.company:
        result.draft_data.company = capture.company
    result.warnings = [warning for warning in result.warnings
        if not (warning.code == 'MISSING_FIELD' and
                ((warning.field == 'title' and capture.title) or (warning.field == 'company' and capture.company)))]
    for warning in result.warnings:
        if warning.code == 'CHECK_DESCRIPTION':
            warning.message = 'The full captured text is kept as the description. Remove unrelated content during review.'
    raw = f'Application URL: {capture.url}\nTitle: {capture.title}\nCompany: {capture.company}\n\n{capture.description}'
    return CapturePreview(**result.model_dump(), raw_text=raw)


def save_capture_draft(service: JobService, user_id, request):
    repo = service.repository
    try:
        repo.lock_owner(user_id)
        preview = preview_capture(request.capture)
        # Include edits in identity: retries are idempotent, revised drafts remain separate.
        fingerprint = sha256(('browser\n' + preview.raw_text + '\n' +
            json.dumps(request.draft_data.model_dump(mode='json'), sort_keys=True)).encode()).hexdigest()
        row = repo.import_by_hash(user_id, fingerprint)
        if row is None:
            row = JobImport(user_id=user_id, source_type='browser', raw_text=preview.raw_text,
                source_hash=fingerprint, parser_version=preview.parser_version,
                draft_data=request.draft_data.model_dump(mode='json'),
                warnings=[warning.model_dump() for warning in preview.warnings])
            repo.add(row)
        repo.commit()
        return service.import_response(row)
    except Exception as error:
        service.handle_error(error)
