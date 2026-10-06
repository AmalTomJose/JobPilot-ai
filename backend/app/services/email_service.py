import secrets
from hashlib import sha256
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.middlewares.exception_middleware import UserException
from app.models.email import EmailConnection, EmailMessage, EmailSyncRun
from app.models.resume_parse import utc_now
from app.services.gmail_client import GmailClient, GmailError, SCOPE, configured, encrypt, decrypt
from app.services.email_text import extract_message, BodyError


def fingerprint(value):
    return sha256(value.encode()).hexdigest()


def epoch(value):
    return int(value.replace(tzinfo=timezone.utc).timestamp())


class EmailService:
    def __init__(self, repository, client=None):
        self.repo = repository
        self.db = repository.db
        self.client = client or GmailClient()

    def require_config(self):
        if not configured():
            raise UserException(503, 'Gmail setup is not configured on this server. Add the Google OAuth credentials and token encryption key.')

    def status(self, user_id):
        row = self.repo.connection(user_id)
        if row is None:
            return dict(configured=configured(), status='disconnected')
        return dict(configured=configured(), has_more=bool(row.page_token), **{key: getattr(row, key) for key in (
            'status', 'mailbox_email', 'label_id', 'label_name', 'import_since', 'auto_sync', 'next_sync_at', 'last_sync_at', 'last_error')})

    def start(self, user_id):
        self.require_config()
        row = self.repo.connection(user_id, lock=True, create=True)
        state, browser, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(32), secrets.token_urlsafe(64)
        row.state_hash, row.browser_hash = fingerprint(state), fingerprint(browser)
        row.state_expires_at = utc_now() + timedelta(minutes=10)
        row.verifier_encrypted = encrypt(verifier)
        self.db.commit()
        return self.client.authorization_url(state, verifier), browser

    def callback(self, state, browser, code=None, denied=False):
        self.require_config()
        if not state or not browser:
            raise UserException(400, 'The connection request expired. Start Connect Gmail again in the same browser.')
        row = self.db.scalar(select(EmailConnection).where(EmailConnection.state_hash == fingerprint(state)).with_for_update(nowait=True))
        if row is None or not row.state_expires_at or row.state_expires_at <= utc_now() or not secrets.compare_digest(row.browser_hash or '', fingerprint(browser)):
            raise UserException(400, 'Invalid or expired Gmail connection request. Start again from Settings.')
        verifier = row.verifier_encrypted
        row.state_hash = row.browser_hash = row.verifier_encrypted = None
        row.state_expires_at = None
        if denied or not code:
            self.db.commit()
            return 'cancelled'
        try:
            tokens = self.client.exchange(code, decrypt(verifier))
            if SCOPE not in tokens.get('scope', '').split() or not tokens.get('access_token'):
                raise GmailError('Read-only Gmail permission was not granted. Connect again and allow Gmail access.')
            profile = self.client.profile(tokens['access_token'])
            mailbox = profile.get('emailAddress', '').strip().casefold()
            if not mailbox or '@' not in mailbox or len(mailbox) > 320:
                raise GmailError('Gmail did not return a valid mailbox identity.')
            if row.mailbox_email and mailbox != row.mailbox_email:
                raise GmailError('A different Gmail account was selected. Disconnect the existing account before switching mailboxes.')
            refresh = tokens.get('refresh_token')
            if not refresh and row.mailbox_email == mailbox and row.refresh_token_encrypted:
                refresh = decrypt(row.refresh_token_encrypted)
            if not refresh:
                raise GmailError('Google did not provide offline access. Remove the old JobPilot grant in Google Account permissions, then reconnect.')
            row.mailbox_email = mailbox
            row.refresh_token_encrypted = encrypt(refresh)
            row.status = 'connected'
            row.last_error = None
            row.failure_count = 0
            if row.auto_sync and row.label_id:
                row.next_sync_at = utc_now()
            self.db.commit()
            return 'connected'
        except GmailError as error:
            row.last_error = str(error)
            self.db.commit()  # Consume the one-time state even on provider failure.
            return 'failed'

    def active_connection(self, user_id):
        self.require_config()
        row = self.repo.connection(user_id, lock=True)
        if row is None or row.status != 'connected' or not row.refresh_token_encrypted:
            raise UserException(409, 'Connect Gmail before continuing.')
        return row

    def token(self, row):
        return self.client.refresh(decrypt(row.refresh_token_encrypted))

    def provider_failure(self, row, error):
        row.last_error = str(error)
        if error.reconnect:
            row.status = 'reconnect_required'
            row.next_sync_at = None

    def labels(self, user_id):
        row = self.active_connection(user_id)
        try:
            labels = self.client.labels(self.token(row))
            # A custom job-alert label is deliberate; no inbox/all-mail default.
            result = sorted([dict(id=item['id'], name=item['name']) for item in labels if item.get('type') == 'user'], key=lambda item: item['name'].casefold())
            self.db.commit()
            return result
        except GmailError as error:
            self.provider_failure(row, error); self.db.commit()
            raise UserException(502, str(error)) from None

    def configure(self, user_id, selection):
        row = self.active_connection(user_id)
        try:
            labels = self.client.labels(self.token(row))
            label = next((item for item in labels if item.get('id') == selection.label_id and item.get('type') == 'user'), None)
            if label is None:
                raise UserException(422, 'Choose an existing custom Gmail label for job alerts.')
            since = datetime.combine(selection.import_since, datetime.min.time())
            if row.label_id != selection.label_id or row.import_since != since:
                row.page_token = None
                row.scan_before = None
            row.label_id, row.label_name, row.import_since = label['id'], label['name'], since
            row.auto_sync = selection.auto_sync
            row.next_sync_at = utc_now() if selection.auto_sync else None
            row.last_error = None
            self.db.commit()
            return self.status(user_id)
        except GmailError as error:
            self.provider_failure(row, error); self.db.commit()
            raise UserException(502, str(error)) from None

    def disconnect(self, user_id):
        row = self.repo.connection(user_id, lock=True)
        if row is None:
            return dict(revoked=True)
        revoked = True
        if row.refresh_token_encrypted:
            try:
                self.client.revoke(decrypt(row.refresh_token_encrypted))
            except GmailError:
                revoked = False
        row.status = 'disconnected'
        row.refresh_token_encrypted = row.state_hash = row.browser_hash = row.verifier_encrypted = None
        row.state_expires_at = row.next_sync_at = row.page_token = row.scan_before = None
        row.mailbox_email = row.label_id = row.label_name = row.import_since = None
        row.auto_sync = False
        row.last_error = None if revoked else 'Local access was removed. Remove JobPilot from Google Account permissions to finish revoking access.'
        self.db.commit()
        return dict(revoked=revoked)

    def save_message(self, row, message_id, token):
        existing = self.repo.message(row.user_id, row.mailbox_email, message_id)
        if existing:
            return 'skipped'
        try:
            data = self.client.message(token, message_id)
        except GmailError as error:
            if error.missing:
                return 'skipped'
            raise
        # A label can change between listing and fetching the actual message.
        if row.label_id not in data.get('labelIds', []):
            return 'skipped'
        payload = data.get('payload', {})
        headers = {h.get('name', '').lower(): h.get('value', '') for h in payload.get('headers', [])}
        try:
            received = datetime.fromtimestamp(int(data['internalDate']) / 1000, tz=timezone.utc).replace(tzinfo=None)
        except (KeyError, ValueError, OverflowError):
            received = None
        if received and received < row.import_since:
            return 'skipped'
        message = EmailMessage(user_id=row.user_id, mailbox_email=row.mailbox_email, provider_message_id=message_id,
                               subject=headers.get('subject', '(No subject)'), sender=headers.get('from', ''),
                               received_at=received, payload_data=payload, status='needs_review')
        try:
            message.raw_text = extract_message(payload)
            from app.services.discovered_service import discover
            from app.repositories.job_repository import JobRepository
            JobRepository(self.db).lock_owner(row.user_id)
            self.db.add(message)
            self.db.flush()
            count = discover(self.db, message)
            message.status = 'discovered' if count or not message.warning else 'needs_review'
        except BodyError as error:
            message.warning = str(error)
        self.db.add(message)
        return 'needs_review' if message.status == 'needs_review' else 'imported'

    def sync(self, user_id, automatic=False):
        row = self.active_connection(user_id)
        if not row.label_id or not row.import_since:
            raise UserException(409, 'Choose a Gmail label and import start date first.')
        if automatic and (not row.auto_sync or row.next_sync_at and row.next_sync_at > utc_now()):
            self.db.rollback()
            return None
        selection_identity = (row.mailbox_email, row.label_id, row.import_since, row.refresh_token_encrypted)
        run = EmailSyncRun(user_id=user_id)
        self.db.add(run); self.db.flush()
        try:
            token = self.token(row)
            if row.scan_before is None:
                row.scan_before = epoch(utc_now()) + 1
            page = self.client.messages(token, row.label_id, epoch(row.import_since)-1, row.scan_before, row.page_token)
            # A bounded page is one transaction; failures do not advance its cursor.
            for item in page.get('messages', []):
                outcome = self.save_message(row, item['id'], token)
                setattr(run, outcome, getattr(run, outcome) + 1)
            row.page_token = page.get('nextPageToken')
            if not row.page_token:
                row.scan_before = None
            row.last_sync_at = utc_now()
            row.last_error = None
            row.failure_count = 0
            row.next_sync_at = utc_now() + timedelta(minutes=5 if row.page_token else 15) if row.auto_sync else None
            run.status = 'completed'
            run.finished_at = utc_now()
            self.db.commit()
            return run
        except GmailError as error:
            # Roll back this page's partial imports, then record a sanitized failure.
            self.db.rollback()
            row = self.repo.connection(user_id, lock=True)
            # Disconnect/reconfiguration can win the lock after rollback; do not
            # reactivate it or overwrite its selection with an old checkpoint.
            if row and row.status == 'connected' and selection_identity == (row.mailbox_email, row.label_id, row.import_since, row.refresh_token_encrypted):
                self.provider_failure(row, error)
                row.failure_count += 1
                if error.invalid_cursor:
                    row.page_token = row.scan_before = None
                if row.status == 'connected' and row.auto_sync:
                    row.next_sync_at = utc_now() + timedelta(seconds=min(900 * 2 ** min(row.failure_count-1, 5), 21600))
            run = EmailSyncRun(user_id=user_id, status='failed', finished_at=utc_now(), error=str(error))
            self.db.add(run); self.db.commit()
            return run
