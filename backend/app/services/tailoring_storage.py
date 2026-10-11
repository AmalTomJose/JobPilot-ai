"""Private, immutable PDF copies created only by explicit approval."""
import re
import unicodedata
from app.core.config import settings
from app.services.tailoring_pdf import render_resume


def resume_filename(data, company):
    def slug(value, fallback):
        ascii_value = unicodedata.normalize('NFKD', value or '').encode('ascii', 'ignore').decode()
        return re.sub(r'[^a-z0-9]+', '_', ascii_value.lower()).strip('_')[:70] or fallback
    name = (data['contact'].get('name') or '').split()
    return f"{slug(name[0] if name else '', 'resume')}_{slug(company, 'company')}_cv.pdf"


def approval_path(row):
    return settings.APPROVED_RESUME_DIR / str(row.user_id) / f'job_{row.job_id}' / f'version_{row.id}' / f'revision_{row.revision}' / resume_filename(row.data, row.job_snapshot.get('company'))


def store_approved_pdf(row):
    """Exclusive creation prevents overwriting another approved revision."""
    pdf = render_resume(row.data, row.section_order)
    path = approval_path(row)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        with path.open('xb') as output:
            path.chmod(0o600)
            output.write(pdf)
    except FileExistsError:
        raise
    except OSError:
        path.unlink(missing_ok=True)
        raise
    return path
