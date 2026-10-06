import unittest
from sqlalchemy import select, func
import test_sprint1
from test_capture import digest
from app.models.email import EmailMessage
from app.models.discovered_job import DiscoveredJob
from app.models.job import Job, JobImport
from app.models.user import User
from app.services.discovered_service import discover
from app.utils.password import hash_password
from app.utils.jwt import create_access_token

class DiscoveredTests(unittest.TestCase):
    setUp = test_sprint1.SprintOneTests.setUp
    tearDown = test_sprint1.SprintOneTests.tearDown

    @classmethod
    def setUpClass(cls):
        cls.password_hash = hash_password('synthetic-test')

    def seed(self, mid='1'):
        with self.sessions() as db:
            row = EmailMessage(user_id=1, mailbox_email='mail@example.com', provider_message_id=mid,
                subject='Job digest', sender='alerts@example.com', payload_data=digest(), raw_text='Two job openings', status='discovered')
            db.add(row); db.flush(); discover(db, row); db.commit()
        return self.client.get('/jobs/discovered', headers=self.headers).json()['items']

    def test_digest_creates_individual_candidates_without_drafts_or_jobs(self):
        rows = self.seed()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row['draft_data']['description'] is None for row in rows))
        with self.sessions() as db:
            for model in (Job, JobImport):
                self.assertEqual(db.scalar(select(func.count()).select_from(model)), 0)

    def test_repeated_email_and_url_preserve_dismissal(self):
        item = self.seed()[0]
        response = self.client.patch(f"/jobs/discovered/{item['id']}", headers=self.headers, json={'status':'dismissed'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.seed('2')), 1)
        self.assertEqual(self.client.get('/jobs/discovered?status=dismissed', headers=self.headers).json()['total'], 1)
        self.assertEqual(self.client.patch(f"/jobs/discovered/{item['id']}", headers=self.headers, json={'status':'pending'}).status_code, 200)

    def test_approval_is_explicit_atomic_and_cannot_repeat(self):
        item = self.seed()[0]
        fields = {**item['draft_data'], 'company':'Reviewed Co', 'description':'A reviewed description'}
        url = f"/jobs/discovered/{item['id']}/approve"
        result = self.client.post(url, headers=self.headers, json=fields)
        self.assertEqual(result.status_code, 201, result.text)
        self.assertEqual(result.json()['company'], 'Reviewed Co')
        candidate = self.client.get(f"/jobs/discovered/{item['id']}", headers=self.headers).json()
        self.assertEqual(candidate['job_id'], result.json()['id'])
        self.assertEqual(candidate['status'], 'approved')
        self.assertEqual(candidate['draft_data']['company'], 'Reviewed Co')
        self.assertEqual(self.client.post(url, headers=self.headers, json=fields).status_code, 409)
        self.assertEqual(self.client.patch(f"/jobs/discovered/{item['id']}", headers=self.headers, json={'status':'dismissed'}).status_code, 409)

    def test_invalid_approval_does_not_change_candidate(self):
        item = self.seed()[0]
        response = self.client.post(f"/jobs/discovered/{item['id']}/approve", headers=self.headers, json={'title':''})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.get('/jobs/discovered', headers=self.headers).json()['total'], 2)

    def test_extension_save_resolves_matching_opening_and_tracking_duplicate(self):
        item = next(row for row in self.seed() if 'linkedin' in row['job_url'])
        fields = {**item['draft_data'], 'application_url':item['job_url']+'?trackingId=one'}
        response = self.client.post('/jobs/capture/save', headers=self.headers, json=fields)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(self.client.get('/jobs/discovered?status=approved', headers=self.headers).json()['total'], 1)
        fields['application_url'] = item['job_url']+'?trackingId=two'
        self.assertEqual(self.client.post('/jobs/capture/save', headers=self.headers, json=fields).status_code, 409)

    def test_other_account_cannot_read_change_or_approve(self):
        item = self.seed()[0]
        with self.sessions() as db:
            db.add(User(name='Other', email='other@example.com', password_hash=self.password_hash)); db.commit()
        other = {'Authorization':f'Bearer {create_access_token(2)}'}
        url = f"/jobs/discovered/{item['id']}"
        self.assertEqual(self.client.get('/jobs/discovered', headers=other).json()['total'], 0)
        self.assertEqual(self.client.get(url, headers=other).status_code, 404)
        self.assertEqual(self.client.patch(url, headers=other, json={'status':'dismissed'}).status_code, 404)
        self.assertEqual(self.client.post(url+'/approve', headers=other, json=item['draft_data']).status_code, 404)
        self.assertEqual(self.client.get('/jobs/discovered').status_code, 401)

    def test_backfill_is_idempotent_and_retains_existing_records(self):
        self.seed()
        result = self.client.post('/jobs/discovered/backfill', headers=self.headers)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()['created'], 0)
        self.assertIsNone(result.json()['next_cursor'])
        with self.sessions() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(EmailMessage)), 1)

    def test_backfill_populates_legacy_email_and_recognizes_saved_job(self):
        with self.sessions() as db:
            db.add(EmailMessage(user_id=1, mailbox_email='mail@example.com', provider_message_id='legacy',
                subject='Older digest', sender='alerts@example.com', payload_data=digest(), raw_text='Two job openings', status='needs_review'))
            db.add(Job(user_id=1, source_type='manual', title='Already saved developer',
                application_url='https://www.linkedin.com/jobs/view/123?trackingId=old', skills=[]))
            db.commit()
        result = self.client.post('/jobs/discovered/backfill', headers=self.headers)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()['created'], 2)
        self.assertEqual(self.client.get('/jobs/discovered', headers=self.headers).json()['total'], 1)
        approved = self.client.get('/jobs/discovered?status=approved', headers=self.headers).json()['items']
        self.assertEqual(len(approved), 1)
        self.assertIsNotNone(approved[0]['job_id'])
        self.assertEqual(self.client.post('/jobs/discovered/backfill', headers=self.headers).json()['created'], 0)

    def test_original_gmail_link_uses_stored_mailbox_and_exact_header(self):
        from urllib.parse import urlsplit, parse_qs, unquote
        item = self.seed()[0]
        with self.sessions() as db:
            message = db.get(EmailMessage, item['email_message_id'])
            message.mailbox_email = 'jobs+alerts@example.com'
            message.payload_data = {**message.payload_data, 'headers':[{'name':'Message-ID', 'value':'<original+id@example.com>'}]}
            db.commit()
        detail = self.client.get(f"/jobs/discovered/{item['id']}", headers=self.headers).json()
        link = urlsplit(detail['gmail_url'])
        self.assertEqual(link.scheme, 'https')
        self.assertEqual(link.netloc, 'mail.google.com')
        self.assertEqual(parse_qs(link.query), {'authuser':['jobs+alerts@example.com']})
        self.assertEqual(unquote(link.fragment), 'search/in:anywhere rfc822msgid:original+id@example.com')
        listing = self.client.get('/jobs/discovered', headers=self.headers).json()['items']
        self.assertEqual(listing[0]['gmail_url'], detail['gmail_url'])
        messages = self.client.get('/email/gmail/messages', headers=self.headers).json()['items']
        self.assertEqual(messages[0]['gmail_url'], detail['gmail_url'])
        self.assertNotIn('payload_data', detail)

    def test_original_gmail_link_has_encoded_fallback_without_header(self):
        from app.services.gmail_links import original_email_url
        from types import SimpleNamespace
        message = SimpleNamespace(mailbox_email='test@example.com', payload_data={}, provider_message_id='id/#?')
        self.assertEqual(original_email_url(message), 'https://mail.google.com/mail/?authuser=test%40example.com#all/id%2F%23%3F')

    def test_source_filter_and_lookup_are_owner_scoped(self):
        self.seed()
        result = self.client.get('/jobs/discovered?site=linkedin&limit=1', headers=self.headers).json()
        self.assertEqual(result['total'], 1)
        item = result['items'][0]
        self.assertEqual(item['source_site'], 'linkedin')
        lookup = self.client.get('/jobs/discovered/lookup', params={'url':item['job_url']+'?trackingId=new'}, headers=self.headers)
        self.assertEqual(lookup.status_code, 200, lookup.text)
        self.assertEqual(lookup.json()[0]['id'], item['id'])
        with self.sessions() as db:
            db.add(User(name='Other', email='other@example.com', password_hash=self.password_hash)); db.commit()
        other = {'Authorization':f'Bearer {create_access_token(2)}'}
        self.assertEqual(self.client.get('/jobs/discovered/lookup', params={'url':item['job_url']}, headers=other).json(), [])
        self.assertEqual(self.client.get('/jobs/discovered?site=unknown', headers=self.headers).status_code, 422)

    def test_provider_urls_and_legacy_decisions(self):
        from app.services.job_sources import source_site, provider_job_id
        from app.services.discovered_service import identity, matching_discoveries
        from app.services.email_candidates import job_link
        urls = [('https://www.naukri.com/job-listings-developer-company-123456789012?src=email', 'naukri'),
                ('https://in.indeed.com/rc/clk?jk=abcdef1234567890&from=email', 'indeed')]
        for url, site in urls:
            self.assertEqual(source_site(url), site)
            self.assertIsNotNone(job_link(url))
        self.assertEqual(identity(urls[0][0]), identity('https://www.naukri.com/job-listings-changed-title-123456789012'))
        self.assertEqual(identity(urls[1][0]), identity('https://www.indeed.com/viewjob?jk=abcdef1234567890'))
        for url in ('https://indeed.com.evil.example/viewjob?jk=abcdef1234567890', 'https://naukri.com@evil.example/jobs', 'http://['):
            self.assertEqual(source_site(url), 'other')
            self.assertIsNone(provider_job_id(url))
        self.assertIsNone(job_link('https://www.indeed.com/jobs?q=developer'))
        item = self.seed()[0]
        with self.sessions() as db:
            row = db.get(DiscoveredJob, item['id'])
            row.job_url = urls[0][0]; row.source_site = 'naukri'; row.status = 'dismissed'
            db.commit()
            matches = matching_discoveries(db, 1, 'https://www.naukri.com/job-listings-other-123456789012')
            self.assertEqual([row.id for row in matches], [item['id']])
            self.assertEqual(matches[0].status, 'dismissed')

    def test_empty_email_backfill_is_safe(self):
        with self.sessions() as db:
            row = EmailMessage(user_id=1, mailbox_email='mail@example.com', provider_message_id='empty', subject='', sender='', payload_data={}, raw_text='', status='needs_review')
            db.add(row); db.flush()
            self.assertEqual(discover(db, row), 0)

    def test_email_link_variants_split_digest_and_replace_placeholder(self):
        import base64
        from hashlib import sha256
        from app.services.email_candidates import extract_openings, job_link
        html = '<a href="https://www.linkedin.com/comm/jobs/view/101/?trackingId=x">Python Developer</a><a href="https://www.linkedin.com/comm/jobs/view/101/?trackingId=y">View job</a><a href="https://www.linkedin.com/comm/jobs/view/102/">Software Engineer</a><a href="https://www.naukri.com/jd/job-listings-engineer-company-123456789012?src=email">Backend Engineer</a><a href="https://www.linkedin.com/comm/jobs/search-results/">See all jobs</a>'
        payload = {'mimeType':'text/html', 'body':{'data':base64.urlsafe_b64encode(html.encode()).decode()}}
        openings = extract_openings(payload)
        self.assertEqual(len(openings), 3)
        self.assertEqual(openings[0].title, 'Python Developer')
        self.assertEqual(openings[0].job_url, 'https://www.linkedin.com/jobs/view/101')
        self.assertNotEqual(job_link('https://linkedin.com.evil.example/comm/jobs/view/101'), 'https://www.linkedin.com/jobs/view/101')
        with self.sessions() as db:
            message = EmailMessage(user_id=1, mailbox_email='mail@example.com', provider_message_id='variants', subject='Jobs', sender='alerts@example.com', payload_data=payload, raw_text='Job openings', status='discovered')
            db.add(message); db.flush()
            db.add(DiscoveredJob(user_id=1, email_message_id=message.id, identity_hash=sha256(('email:'+str(message.id)).encode()).hexdigest(), draft_data={}, raw_text='Job openings', warnings=[], parser_version='old', status='pending'))
            db.flush()
            self.assertEqual(discover(db, message), 3)
            db.flush()
            self.assertEqual(db.scalar(select(func.count()).select_from(DiscoveredJob)), 3)
            self.assertEqual(discover(db, message), 0)
            self.assertEqual(db.scalar(select(func.count()).select_from(Job)), 0)
