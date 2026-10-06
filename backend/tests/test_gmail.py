import base64
from datetime import datetime, timedelta, timezone
import logging
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from cryptography.fernet import Fernet
from sqlalchemy import select, func
import test_sprint1
from app.core.config import settings
from app.core.oauth_logging import OAuthAccessFilter
from app.models.email import EmailConnection, EmailMessage, EmailSyncRun
from app.models.discovered_job import DiscoveredJob
from app.models.job import JobImport, Job
from app.models.user import User
from app.models.resume_parse import utc_now
from app.repositories.email_repository import EmailRepository
from app.services.email_service import EmailService, fingerprint
from app.services.email_text import extract_message, BodyError
from app.services.gmail_client import GmailClient, GmailError, SCOPE, encrypt, decrypt
from app.utils.password import hash_password
from app.utils.jwt import create_access_token


def payload(text='Title: Engineer\nCompany: Example\nSkills: Python', mime='text/plain'):
    return {'mimeType': mime, 'headers': [{'name': 'Subject', 'value': 'Job opening'}, {'name': 'From', 'value': 'alerts@example.com'}],
            'body': {'data': base64.urlsafe_b64encode(text.encode()).decode().rstrip('=')}}


def message(message_id='m1', text=None):
    return {'id': message_id, 'labelIds': ['Label_Jobs'], 'internalDate': str(int(datetime.now(timezone.utc).timestamp()*1000)), 'payload': payload() if text is None else payload(text)}


class FakeGoogle(GmailClient):
    def __init__(self):
        self.calls = []
        self.page = {'messages': [{'id': 'm1'}]}
        self.bodies = {'m1': message()}
        self.failure = None
        self.mailbox = 'mailbox@example.com'
        self.scopes = SCOPE

    def exchange(self, code, verifier):
        self.calls.append(('exchange', code, verifier))
        return {'access_token': 'private-access', 'refresh_token': 'private-refresh', 'scope': self.scopes}

    def profile(self, token):
        return {'emailAddress': self.mailbox}

    def refresh(self, token):
        if self.failure:
            raise self.failure
        return 'private-access'

    def labels(self, token):
        return [{'id': 'Label_Jobs', 'name': 'Job Alerts', 'type': 'user'}, {'id': 'INBOX', 'name': 'Inbox', 'type': 'system'}]

    def messages(self, token, label, since, before, page_token=None):
        self.calls.append(('messages', label, since, before, page_token))
        return self.page

    def message(self, token, message_id):
        value = self.bodies[message_id]
        if isinstance(value, Exception):
            raise value
        return value

    def revoke(self, token):
        self.calls.append(('revoke', token))
        if self.failure:
            raise self.failure
        return {}


class MimeTests(unittest.TestCase):
    def test_plain_and_alternative_not_duplicated(self):
        part = {'mimeType': 'multipart/alternative', 'parts': [payload('Plain original'), payload('<p>HTML duplicate</p>', 'text/html')]}
        self.assertEqual(extract_message(part), 'Plain original')

    def test_empty_plain_body_falls_back_to_html(self):
        part = {'mimeType': 'multipart/alternative', 'parts': [payload(''), payload('<p>Job details</p>', 'text/html')]}
        self.assertEqual(extract_message(part), 'Job details')

    def test_html_links_kept_scripts_not_executed_or_included(self):
        text = extract_message(payload('<style>secret</style><script>evil()</script><p>Title: Engineer</p><a href="https://example.com/jobs/1">Apply now</a><img src="https://tracker.invalid/pixel"><a href="javascript:alert(1)">bad link</a>', 'text/html'))
        self.assertIn('Apply now https://example.com/jobs/1', text)
        for absent in ('evil()', 'secret', 'javascript:', 'tracker.invalid'):
            self.assertNotIn(absent, text)

    def test_attachments_ignored_and_missing_body_reported(self):
        part = payload('Not a body'); part['filename'] = 'attached.txt'
        with self.assertRaises(BodyError): extract_message(part)
        with self.assertRaises(BodyError): extract_message({'mimeType': 'text/plain', 'body': {'attachmentId': 'x'}})

    def test_invalid_encoding_and_long_body_reported(self):
        for part in (payload('x'*100001), {'mimeType': 'text/plain', 'body': {'data': '!invalid!'}}):
            with self.assertRaises(BodyError): extract_message(part)

    def test_oauth_access_logs_redact_query(self):
        record = logging.LogRecord('uvicorn.access', 20, '', 0, '%s %s %s %s %s', ('client', 'GET', '/email/gmail/callback?code=SECRET&state=STATE', '1.1', 303), None)
        OAuthAccessFilter().filter(record)
        self.assertNotIn('SECRET', record.getMessage())
        self.assertNotIn('STATE', record.getMessage())


class GmailTests(unittest.TestCase):
    tearDownBase = test_sprint1.SprintOneTests.tearDown

    @classmethod
    def setUpClass(cls):
        cls.password_hash = hash_password('synthetic-gmail-test')

    def setUp(self):
        test_sprint1.SprintOneTests.setUp(self)
        self.patches = [patch.object(settings, name, value) for name, value in {
            'GMAIL_CLIENT_ID': 'test-client', 'GMAIL_CLIENT_SECRET': 'test-secret',
            'GMAIL_TOKEN_ENCRYPTION_KEY': Fernet.generate_key().decode(),
            'GMAIL_REDIRECT_URI': 'http://localhost:8000/email/gmail/callback',
            'FRONTEND_URL': 'http://localhost:5173',
        }.items()]
        for item in self.patches: item.start()
        self.google = FakeGoogle()
        self.client_patch = patch('app.services.email_service.GmailClient', return_value=self.google)
        self.client_patch.start()

    def tearDown(self):
        self.client_patch.stop()
        for item in reversed(self.patches): item.stop()
        self.tearDownBase()

    def connect(self):
        result = self.client.post('/email/gmail/connect', headers=self.headers)
        self.assertEqual(result.status_code, 200, result.text)
        query = parse_qs(urlsplit(result.json()['authorization_url']).query)
        return query['state'][0]

    def authorize(self):
        state = self.connect()
        result = self.client.get('/email/gmail/callback', params={'state': state, 'code': 'code'}, follow_redirects=False)
        self.assertEqual(result.status_code, 303, result.text)
        self.assertIn('gmail=connected', result.headers['location'])
        return result

    def select(self, automatic=False):
        result = self.client.put('/email/gmail/selection', headers=self.headers, json={'label_id': 'Label_Jobs', 'import_since': '2026-01-01', 'auto_sync': automatic})
        self.assertEqual(result.status_code, 200, result.text)

    def sync(self):
        result = self.client.post('/email/gmail/sync', headers=self.headers)
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()

    def test_deleted_message_does_not_block_batch(self):
        self.authorize()
        self.select()
        self.google.bodies['m1'] = GmailError('Message removed', missing=True)
        run = self.sync()
        self.assertEqual(run['status'], 'completed')
        self.assertEqual(run['skipped'], 1)

    def test_config_is_optional_and_secrets_not_returned(self):
        with patch.object(settings, 'GMAIL_CLIENT_SECRET', ''):
            self.assertFalse(self.client.get('/email/gmail', headers=self.headers).json()['configured'])
            self.assertEqual(self.client.post('/email/gmail/connect', headers=self.headers).status_code, 503)
        self.authorize()
        result = self.client.get('/email/gmail', headers=self.headers).text
        for secret in ('private-refresh', 'private-access', 'test-secret', 'encrypted', 'state_hash'):
            self.assertNotIn(secret, result)
        with self.sessions() as db:
            stored = db.scalar(select(EmailConnection)).refresh_token_encrypted
            self.assertNotEqual(stored, 'private-refresh')
            self.assertEqual(decrypt(stored), 'private-refresh')

    def test_oauth_state_browser_binding_expiry_replay_and_pkce(self):
        state = self.connect()
        with self.sessions() as db:
            row = db.scalar(select(EmailConnection))
            self.assertEqual(row.state_hash, fingerprint(state))
            self.assertNotIn(state, row.verifier_encrypted)
        browser = self.client.cookies.get('jobpilot_gmail_oauth')
        self.client.cookies.clear()
        self.assertEqual(self.client.get('/email/gmail/callback', params={'state':state,'code':'x'}).status_code, 400)
        self.client.cookies.set('jobpilot_gmail_oauth', browser)
        success = self.client.get('/email/gmail/callback', params={'state':state,'code':'x'}, follow_redirects=False)
        self.assertEqual(success.status_code, 303)
        self.assertTrue(self.google.calls[0][2])
        self.assertEqual(self.client.get('/email/gmail/callback', params={'state':state,'code':'x'}).status_code, 400)
        state = self.connect()
        with self.sessions() as db:
            db.scalar(select(EmailConnection)).state_expires_at = utc_now()-timedelta(seconds=1); db.commit()
        self.assertEqual(self.client.get('/email/gmail/callback', params={'state':state,'code':'x'}).status_code, 400)

    def test_denial_and_missing_scope_do_not_connect(self):
        state = self.connect()
        result = self.client.get('/email/gmail/callback', params={'state':state,'error':'access_denied'}, follow_redirects=False)
        self.assertIn('cancelled', result.headers['location'])
        self.assertFalse(self.google.calls)
        self.google.scopes = 'unrelated'
        state = self.connect()
        result = self.client.get('/email/gmail/callback', params={'state':state,'code':'x'}, follow_redirects=False)
        self.assertIn('failed', result.headers['location'])
        self.assertEqual(self.client.get('/email/gmail', headers=self.headers).json()['status'], 'disconnected')

    def test_different_mailbox_requires_disconnect(self):
        self.authorize()
        self.google.mailbox = 'different@example.com'
        state = self.connect()
        result = self.client.get('/email/gmail/callback', params={'state':state,'code':'x'}, follow_redirects=False)
        self.assertIn('failed', result.headers['location'])
        self.assertEqual(self.client.get('/email/gmail', headers=self.headers).json()['mailbox_email'], 'mailbox@example.com')

    def test_only_custom_labels_and_dates_accepted(self):
        self.authorize()
        self.assertEqual(self.client.get('/email/gmail/labels', headers=self.headers).json(), [{'id':'Label_Jobs','name':'Job Alerts'}])
        self.assertEqual(self.client.post('/email/gmail/sync', headers=self.headers).status_code, 409)
        for value in ({'label_id':'INBOX','import_since':'2026-01-01'}, {'label_id':'Label_Jobs','import_since':'2999-01-01'}):
            self.assertEqual(self.client.put('/email/gmail/selection',headers=self.headers,json=value).status_code,422)

    def test_sync_discovers_without_drafts_preserves_source_and_deduplicates(self):
        self.authorize(); self.select()
        self.assertEqual(self.sync()['imported'], 1)
        self.assertEqual(self.sync()['skipped'], 1)
        messages = self.client.get('/email/gmail/messages',headers=self.headers).json()
        self.assertEqual(messages['total'], 1)
        self.assertNotIn('payload_data', str(messages))
        self.assertIsNone(messages['items'][0]['import_id'])
        imported = self.client.get('/jobs/discovered', headers=self.headers).json()['items'][0]
        self.assertEqual(imported['draft_data']['title'], 'Engineer')
        self.assertIn('Subject: Job opening', imported['raw_text'])
        with self.sessions() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Job)), 0)
            self.assertEqual(db.scalar(select(EmailMessage)).payload_data, payload())

    def test_pagination_keeps_window_and_restarts_after_completion(self):
        self.authorize(); self.select()
        self.google.page['nextPageToken'] = 'next'
        self.sync()
        self.assertTrue(self.client.get('/email/gmail',headers=self.headers).json()['has_more'])
        first = [c for c in self.google.calls if c[0]=='messages'][-1]
        self.google.page = {'messages': []}
        self.sync()
        second = [c for c in self.google.calls if c[0]=='messages'][-1]
        self.assertEqual(first[3], second[3])
        self.assertEqual(second[4], 'next')
        self.assertFalse(self.client.get('/email/gmail',headers=self.headers).json()['has_more'])

    def test_partial_page_failure_rolls_back_imports_and_cursor(self):
        self.authorize(); self.select(True)
        self.google.page = {'messages':[{'id':'m1'},{'id':'m2'}], 'nextPageToken':'lost'}
        self.google.bodies['m2'] = GmailError('Try again later')
        self.assertEqual(self.sync()['status'], 'failed')
        with self.sessions() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(JobImport)), 0)
            self.assertEqual(db.scalar(select(func.count()).select_from(EmailMessage)), 0)
            row = db.scalar(select(EmailConnection))
            self.assertIsNone(row.page_token)
            self.assertGreater(row.next_sync_at, utc_now())
        self.google.bodies['m2'] = message('m2', 'Title: Designer')
        self.assertEqual(self.sync()['imported'], 2)

    def test_revocation_disables_worker_until_reconnect(self):
        self.authorize(); self.select(True)
        self.google.failure = GmailError('Reconnect Gmail', reconnect=True)
        self.assertEqual(self.sync()['status'], 'failed')
        state = self.client.get('/email/gmail', headers=self.headers).json()
        self.assertEqual(state['status'], 'reconnect_required')
        self.assertIsNone(state['next_sync_at'])

    def test_multi_job_and_unsupported_mime_need_review(self):
        self.authorize(); self.select()
        self.google.page = {'messages':[{'id':'m1'},{'id':'m2'}]}
        self.google.bodies['m1'] = message('m1', 'Title: Engineer\nTitle: Designer')
        self.google.bodies['m2'] = message('m2'); self.google.bodies['m2']['payload'] = {'mimeType':'application/pdf','body':{}}
        self.assertEqual(self.sync()['needs_review'], 2)
        rows = self.client.get('/email/gmail/messages', headers=self.headers).json()['items']
        self.assertTrue(all(row['warning'] for row in rows))
        self.assertEqual(sum(row['import_id'] is not None for row in rows), 0)

    def test_changed_label_between_list_and_fetch_is_skipped(self):
        self.authorize(); self.select()
        self.google.bodies['m1']['labelIds'] = ['INBOX']
        self.assertEqual(self.sync()['skipped'], 1)
        self.assertEqual(self.client.get('/email/gmail/messages',headers=self.headers).json()['total'],0)

    def test_disconnect_removes_secrets_preserves_imports_even_when_revoke_fails(self):
        self.authorize(); self.select(); self.sync()
        self.google.failure = GmailError('Unavailable')
        result = self.client.delete('/email/gmail', headers=self.headers)
        self.assertEqual(result.json(), {'revoked': False})
        with self.sessions() as db:
            row = db.scalar(select(EmailConnection))
            self.assertIsNone(row.refresh_token_encrypted)
            self.assertFalse(row.auto_sync)
            self.assertEqual(db.scalar(select(func.count()).select_from(JobImport)), 0)
            self.assertEqual(db.scalar(select(func.count()).select_from(DiscoveredJob)), 1)
        self.assertEqual(self.client.post('/email/gmail/sync',headers=self.headers).status_code,409)

    def test_endpoints_are_authenticated_and_owner_scoped(self):
        self.authorize(); self.select(); self.sync()
        with self.sessions() as db:
            user = User(name='Other',email='other@example.com',password_hash=self.password_hash); db.add(user); db.commit(); uid=user.id
        headers = {'Authorization':f'Bearer {create_access_token(uid)}'}
        for path in ('','/labels','/messages','/runs'):
            self.assertEqual(self.client.get('/email/gmail'+path).status_code,401)
        for path in ('/connect','/sync'):
            self.assertEqual(self.client.post('/email/gmail'+path).status_code,401)
        self.assertEqual(self.client.delete('/email/gmail').status_code,401)
        self.assertEqual(self.client.get('/email/gmail',headers=headers).json()['status'],'disconnected')
        self.assertEqual(self.client.get('/email/gmail/messages',headers=headers).json()['total'],0)
        self.assertEqual(self.client.get('/email/gmail/runs',headers=headers).json(),[])
        self.assertEqual(self.client.get('/email/gmail/messages?offset=-1',headers=self.headers).status_code,422)

    def test_worker_only_processes_opted_in_due_connections(self):
        from app.workers.gmail_worker import tick
        self.authorize(); self.select(False)
        self.assertEqual(tick(self.sessions),0)
        self.select(True)
        self.assertEqual(tick(self.sessions),1)
        self.assertEqual(tick(self.sessions),0)


class GmailTransportTests(unittest.TestCase):
    def request(self, status, data):
        import httpx
        original = httpx.Client
        transport = httpx.MockTransport(lambda request: httpx.Response(status, json=data))
        with patch('app.services.gmail_client.httpx.Client', side_effect=lambda **kwargs: original(transport=transport, **kwargs)):
            return GmailClient().request('GET', 'https://gmail.googleapis.com/test')

    def test_provider_errors_are_sanitized_and_classified(self):
        for status, flag in ((401, 'reconnect'), (404, 'missing'), (400, 'invalid_cursor'), (429, None)):
            with self.assertRaises(GmailError) as caught:
                self.request(status, {'error': 'private-provider-detail'})
            self.assertNotIn('private-provider-detail', str(caught.exception))
            if flag:
                self.assertTrue(getattr(caught.exception, flag))

    def test_malformed_or_oversize_response_is_rejected(self):
        for data in ([], {'body': 'x' * 2_000_001}):
            with self.assertRaises(GmailError):
                self.request(200, data)
