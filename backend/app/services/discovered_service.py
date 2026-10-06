"""Discovery never approves a job or creates an editable JobImport."""
from contextlib import contextmanager
from hashlib import sha256
from sqlalchemy import select, func
from app.models.discovered_job import DiscoveredJob
from app.models.email import EmailMessage
from app.models.job import Job
from app.repositories.job_repository import JobRepository
from app.services.email_candidates import extract_openings
from app.services.job_sources import source_site, provider_job_id
from app.services.job_parser import parse_job_email, canonical_url
from app.schemas.job import JobFields
from app.middlewares.exception_middleware import UserException


def identity(url):
    from app.services.email_candidates import job_link
    # Normalize known provider URLs before the general tracking-parameter cleanup.
    provider = provider_job_id(url) if url else None
    value = ':'.join(provider) if provider else canonical_url(job_link(url) or url) if url else None
    return sha256(value.encode()).hexdigest() if value else None


def matching_discoveries(db, user_id, url):
    key = identity(url)
    if not key:
        return []
    rows = list(db.scalars(select(DiscoveredJob).where(DiscoveredJob.user_id == user_id, DiscoveredJob.identity_hash == key)))
    # Old rows used generic URL hashes. Compare explicit provider IDs without
    # rewriting/deleting historical rows or losing approved/dismissed decisions.
    if provider_job_id(url):
        for row in db.scalars(select(DiscoveredJob).where(DiscoveredJob.user_id == user_id,
                DiscoveredJob.source_site == source_site(url), DiscoveredJob.job_url.is_not(None))):
            if row not in rows and identity(row.job_url) == key:
                rows.append(row)
    return rows


def discover(db, message):
    if not (message.raw_text or '').strip():
        return 0
    openings = extract_openings(message.payload_data, message.raw_text)
    parsed = parse_job_email(message.raw_text or '')
    multiple = len(openings) > 1 or any(w.code == 'MULTIPLE_JOBS' for w in parsed.warnings)
    # Never turn an unseparated digest into one combined job.
    if not openings and multiple:
        message.warning = 'Several jobs were detected but individual links could not be identified. Open the original email and import one description at a time.'
        return 0
    if not openings and not parsed.draft_data.title:
        message.warning = 'No individual job identified. Open the original email to check it.'
        return 0
    # Replace only the untouched, linkless placeholder produced by older parsers.
    # Approved/dismissed decisions and real per-job candidates are preserved.
    if openings:
        fallback_key = sha256(('email:' + str(message.id)).encode()).hexdigest()
        placeholder = db.scalar(select(DiscoveredJob).where(
            DiscoveredJob.user_id == message.user_id,
            DiscoveredJob.email_message_id == message.id,
            DiscoveredJob.identity_hash == fallback_key,
            DiscoveredJob.job_url.is_(None),
            DiscoveredJob.status == 'pending',
            DiscoveredJob.job_id.is_(None)))
        if placeholder is not None:
            db.delete(placeholder)
        message.warning = None
    created = 0
    for opening in openings or [None]:
        url = opening.job_url if opening else parsed.draft_data.application_url
        key = identity(url) or sha256(('email:' + str(message.id)).encode()).hexdigest()
        found = matching_discoveries(db, message.user_id, url) if url else db.scalar(select(DiscoveredJob.id).where(DiscoveredJob.user_id == message.user_id, DiscoveredJob.identity_hash == key))
        if found:
            continue
        # Multiple openings have no reliable per-job description in a digest.
        fields = JobFields(title=opening.title, application_url=url) if multiple else parsed.draft_data.model_copy(deep=True)
        if opening:
            fields.application_url = url
            if opening.title:
                fields.title = opening.title
        warnings = [w.model_dump() for w in parsed.warnings] if not multiple else []
        if multiple:
            warnings.append(dict(code='DESCRIPTION_NEEDED', field='description', message='Open this job and add its full description. The email contains several openings.'))
        else:
            warnings.append(dict(code='VERIFY_DESCRIPTION', field='description', message='Email text may be only a summary. Check the original job description before approving.'))
        existing = db.scalar(select(Job).where(Job.user_id == message.user_id, Job.source_import_id == message.import_id)) if message.import_id and not multiple else None
        if existing is None and url:
            # Existing jobs may predate provider-specific URL normalization.
            existing = next((job for job in db.scalars(select(Job).where(Job.user_id == message.user_id, Job.application_url.is_not(None))) if identity(job.application_url) == key), None)
        if existing:
            fields = JobFields.model_validate(existing, from_attributes=True)
        row = DiscoveredJob(user_id=message.user_id, email_message_id=message.id, identity_hash=key,
            source_site=source_site(url), job_url=url, draft_data=fields.model_dump(mode='json'), raw_text=(message.raw_text or '') if not multiple else f'{opening.title or "Opening"}\n{url}',
            warnings=warnings, parser_version=parsed.parser_version,
            status='approved' if existing else 'pending', job_id=existing.id if existing else None)
        db.add(row)
        db.flush()
        created += 1
    return created


def get(db, user_id, candidate_id):
    row = db.scalar(select(DiscoveredJob).where(DiscoveredJob.user_id == user_id, DiscoveredJob.id == candidate_id))
    if row is None:
        raise UserException(404, 'Discovered job not found')
    return row


def listing(db, user_id, status, limit, offset, site=None):
    query = select(DiscoveredJob).where(DiscoveredJob.user_id == user_id, DiscoveredJob.status == status)
    if site:
        query = query.where(DiscoveredJob.source_site == site)
    return dict(items=list(db.scalars(query.order_by(DiscoveredJob.id.desc()).limit(limit).offset(offset))),
        total=db.scalar(select(func.count()).select_from(query.subquery())), limit=limit, offset=offset)


@contextmanager
def mutation(db, user_id):
    from app.services.job_service import JobService
    repo = JobRepository(db)
    try:
        repo.lock_owner(user_id)
        yield
        db.commit()
    except Exception as error:
        JobService(repo).handle_error(error)


def set_status(db, user_id, candidate_id, status):
    with mutation(db, user_id):
        row = get(db, user_id, candidate_id)
        if row.status == 'approved':
            raise UserException(409, 'This opportunity is already saved. Manage it in Saved jobs.')
        row.status = status
    return row


def backfill(db, user_id, after_id):
    with mutation(db, user_id):
        rows = list(db.scalars(select(EmailMessage).where(EmailMessage.user_id == user_id, EmailMessage.id > after_id).order_by(EmailMessage.id).limit(100)))
        count = sum(discover(db, row) for row in rows)
    return dict(created=count, next_cursor=rows[-1].id if len(rows) == 100 else None)
