"""Run with python -m app.workers.gmail_worker [--once]. No mailbox access without opt-in."""
import argparse
import logging
import time
from sqlalchemy import select
from app.database.database import SessionLocal
from app.models.user import User
from app.models.profile import Profile
from app.models.resume import Resume
from app.models.resume_parse import utc_now
from app.models.job import Job, JobImport
from app.models.email import EmailConnection
from app.repositories.email_repository import EmailRepository
from app.services.email_service import EmailService
from app.services.gmail_client import configured

logger = logging.getLogger(__name__)


def tick(session_factory=SessionLocal):
    if not configured():
        return 0
    with session_factory() as db:
        owners = list(db.scalars(select(EmailConnection.user_id).where(
            EmailConnection.status == 'connected', EmailConnection.auto_sync.is_(True),
            EmailConnection.label_id.is_not(None), EmailConnection.next_sync_at <= utc_now()).order_by(EmailConnection.next_sync_at).limit(50)))
    processed = 0
    for owner in owners:
        with session_factory() as db:
            try:
                result = EmailService(EmailRepository(db)).sync(owner, automatic=True)
                processed += result is not None
            except Exception:
                db.rollback()
                # No tokens, mailbox content, URLs, or provider exception text in logs.
                logger.warning('A Gmail sync could not run; it will be retried on a later worker pass.')
    return processed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    if not configured():
        raise SystemExit('Configure Gmail OAuth and encryption settings before starting the worker.')
    while True:
        tick()
        if args.once:
            break
        time.sleep(30)


if __name__ == '__main__':
    main()
