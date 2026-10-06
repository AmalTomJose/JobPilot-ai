import base64
import unittest
from sqlalchemy import select, func
import test_sprint1
from app.models.job import Job, JobImport
from app.models.email import EmailMessage
from app.models.user import User
from app.services.email_candidates import extract_openings, job_link
from app.utils.password import hash_password
from app.utils.jwt import create_access_token


def digest():
    html = '<a href="https://www.linkedin.com/jobs/view/123?trackingId=abc">Python Developer</a><a href="https://www.linkedin.com/jobs/view/123?trk=abc">Apply</a><a href="https://jobs.lever.co/example/00000000-0000-0000-0000-000000000001">Web Developer</a><a href="https://www.linkedin.com/messaging">Messages</a>'
    return {'mimeType': 'multipart/alternative', 'parts': [
        {'mimeType': 'text/plain', 'body': {'data': base64.urlsafe_b64encode(b'Two job openings').decode()}},
        {'mimeType': 'text/html', 'body': {'data': base64.urlsafe_b64encode(html.encode()).decode()}}]}


class OpeningTests(unittest.TestCase):
    def test_html_links_survive_plain_text_preference_and_deduplicate(self):
        items = extract_openings(digest(), 'Two job openings')
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].title, 'Python Developer')
        self.assertEqual(items[0].job_url, 'https://www.linkedin.com/jobs/view/123')

    def test_unsafe_or_unrelated_links_are_not_job_cards(self):
        for url in ('javascript:alert(1)', 'https://user:pass@example.com/jobs/1',
                    'http://127.0.0.1/jobs/1', 'http://localhost/jobs/1', 'http://intranet.local/jobs/1',
                    'https://linkedin.com/messaging', 'https://linkedin.com/jobs/search'):
            self.assertIsNone(job_link(url), url)


class CaptureTests(unittest.TestCase):
    setUp = test_sprint1.SprintOneTests.setUp
    tearDown = test_sprint1.SprintOneTests.tearDown

    @classmethod
    def setUpClass(cls):
        cls.password_hash = hash_password('synthetic-test')
        cls.capture = dict(title='Python Developer', company='Example', url='https://example.com/jobs/1',
            description='Build backend services. Required skills: Python, PostgreSQL. Collaborate with the engineering team.')

    def preview(self):
        response = self.client.post('/jobs/capture/preview', headers=self.headers, json=self.capture)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def counts(self):
        with self.sessions() as db:
            return (db.scalar(select(func.count()).select_from(JobImport)), db.scalar(select(func.count()).select_from(Job)))

    def test_preview_and_repeated_preview_never_save_records(self):
        data = self.preview()
        self.preview()
        self.assertEqual(data['draft_data']['description'], self.capture['description'])
        self.assertEqual(data['draft_data']['application_url'], self.capture['url'])
        self.assertEqual(self.counts(), (0, 0))
        self.assertFalse(any(w['code'] == 'MISSING_FIELD' and w['field'] in {'title','company'} for w in data['warnings']))

    def test_add_to_jobs_has_browser_source_and_no_draft(self):
        data = self.preview()['draft_data']
        result = self.client.post('/jobs/capture/save', headers=self.headers, json=data)
        self.assertEqual(result.status_code, 201, result.text)
        self.assertEqual(result.json()['source_type'], 'browser')
        self.assertIsNone(result.json()['source_import_id'])
        self.assertEqual(self.counts(), (0, 1))
        self.assertEqual(self.client.post('/jobs/capture/save', headers=self.headers, json=data).status_code, 409)

    def test_explicit_draft_preserves_edits_and_retry_is_idempotent(self):
        data = self.preview()['draft_data']
        data['company'] = 'Reviewed company'
        request = {'capture': self.capture, 'draft_data': data}
        first = self.client.post('/jobs/capture/drafts', headers=self.headers, json=request)
        second = self.client.post('/jobs/capture/drafts', headers=self.headers, json=request)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()['id'], second.json()['id'])
        self.assertEqual(first.json()['draft_data']['company'], 'Reviewed company')
        self.assertEqual(self.counts(), (1, 0))
        saved = self.client.post('/jobs', headers=self.headers, json={**data, 'import_id':first.json()['id']})
        self.assertEqual(saved.status_code, 201, saved.text)
        self.assertEqual(saved.json()['source_type'], 'browser')

    def test_auth_and_invalid_payloads(self):
        self.assertEqual(self.client.post('/jobs/capture/preview', json=self.capture).status_code, 401)
        for changes in ({'url':'javascript:alert(1)'}, {'description':'short'}, {'description':'x'*20001}, {'user_id':99}):
            response = self.client.post('/jobs/capture/preview', headers=self.headers, json={**self.capture, **changes})
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.counts(), (0, 0))

    def test_saved_drafts_are_owner_scoped(self):
        with self.sessions() as db:
            db.add(User(name='Other', email='other@example.com', password_hash=self.password_hash))
            db.commit()
        imported = self.client.post('/jobs/capture/drafts', headers=self.headers,
            json={'capture':self.capture, 'draft_data':self.preview()['draft_data']}).json()
        other = {'Authorization':f'Bearer {create_access_token(2)}'}
        self.assertEqual(self.client.get(f"/jobs/imports/{imported['id']}", headers=other).status_code,404)

    def test_preexisting_email_gets_cards_without_draft_writes(self):
        with self.sessions() as db:
            db.add(EmailMessage(user_id=1, mailbox_email='mail@example.com', provider_message_id='123', subject='Digest',
                sender='alerts@example.com', payload_data=digest(), raw_text='Two job openings', status='needs_review'))
            db.commit()
        response = self.client.get('/email/gmail/messages', headers=self.headers)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(len(response.json()['items'][0]['openings']),2)
        self.assertNotIn('payload_data',response.json()['items'][0])
        self.assertEqual(self.counts(),(0,0))
