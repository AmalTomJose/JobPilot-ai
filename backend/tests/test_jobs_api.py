import unittest
from unittest.mock import patch
from pathlib import Path
from sqlalchemy import select, func
import test_sprint1
from app.models.job import Job, JobImport
from app.models.user import User
from app.utils.password import hash_password
from app.utils.jwt import create_access_token


class JobAPITests(unittest.TestCase):
    setUp = test_sprint1.SprintOneTests.setUp
    tearDown = test_sprint1.SprintOneTests.tearDown

    @classmethod
    def setUpClass(cls):
        cls.password_hash = hash_password('synthetic-test')
        cls.source = (Path(__file__).parent / 'fixtures/jobs/labeled.txt').read_text()

    def create(self, **changes):
        payload = {'title':'Backend Developer', 'company':'Example', 'skills':['Python'], **changes}
        return self.client.post('/jobs', headers=self.headers, json=payload)

    def import_email(self, source=None, headers=None):
        response = self.client.post('/jobs/imports', headers=headers or self.headers, json={'raw_text':self.source if source is None else source})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def update(self, job, **changes):
        fields = {key:job[key] for key in ('title','company','location','work_mode','employment_type','description','skills','application_url')}
        fields.update(expected_revision=job['revision'], status=job['status']); fields.update(changes)
        return self.client.put(f'/jobs/{job["id"]}', headers=self.headers, json=fields)

    def test_manual_job_round_trip_and_unknowns(self):
        response = self.create(description='<script>plain text only</script>')
        self.assertEqual(response.status_code, 201, response.text)
        job = response.json()
        self.assertEqual(job['source_type'], 'manual')
        self.assertIsNone(job['source'])
        self.assertIsNone(job['location'])
        self.assertEqual(job['revision'], 1)
        self.assertEqual(self.client.get(f'/jobs/{job["id"]}', headers=self.headers).json(), job)

    def test_email_review_saves_independently_from_source(self):
        imported = self.import_email()
        job = self.create(title='Corrected title', import_id=imported['id'], application_url=imported['draft_data']['application_url']).json()
        self.assertEqual(job['source_type'], 'email')
        self.assertEqual(job['title'], 'Corrected title')
        self.assertEqual(job['source']['raw_text'], self.source)
        self.assertEqual(job['source']['draft_data']['title'], 'Backend Developer')
        self.assertEqual(self.client.get('/jobs/imports', headers=self.headers).json()['total'], 0)
        self.assertNotIn('raw_text', self.client.get('/jobs', headers=self.headers).json()['items'][0])

    def test_same_email_reuses_import_and_reports_saved_duplicate(self):
        first = self.import_email()
        second = self.import_email()
        self.assertEqual(first['id'], second['id'])
        saved = self.create(import_id=first['id']).json()
        third = self.import_email()
        self.assertEqual(third['duplicate']['id'], saved['id'])
        blocked = self.create(import_id=first['id'], application_url='https://example.com/different')
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(blocked.json()['details']['duplicate']['id'], saved['id'])
        with self.sessions() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(JobImport)), 1)

    def test_extract_again_refreshes_only_unsaved_old_version_imports(self):
        imported = self.import_email()
        with self.sessions() as db:
            row = db.get(JobImport, imported['id'])
            row.parser_version = 'job-rules-v1'
            row.draft_data = {**row.draft_data, 'title': None}
            db.commit()
        refreshed = self.import_email()
        self.assertEqual(refreshed['id'], imported['id'])
        self.assertEqual(refreshed['raw_text'], self.source)
        self.assertEqual(refreshed['parser_version'], 'job-rules-v3')
        self.assertEqual(refreshed['draft_data']['title'], 'Backend Developer')
        saved = self.create(import_id=imported['id'], title='Reviewed title').json()
        with self.sessions() as db:
            db.get(JobImport, imported['id']).parser_version = 'job-rules-v1'
            db.commit()
        unchanged = self.import_email()
        self.assertEqual(unchanged['parser_version'], 'job-rules-v1')
        self.assertEqual(unchanged['duplicate']['id'], saved['id'])
        self.assertEqual(self.client.get(f'/jobs/{saved["id"]}', headers=self.headers).json()['title'], 'Reviewed title')

    def test_url_duplicates_normalize_tracking_and_include_archived(self):
        job = self.create(application_url='https://EXAMPLE.com:443/jobs?id=123&utm_source=x#apply').json()
        self.assertEqual(self.update(job,status='archived').status_code, 200)
        response = self.create(application_url='https://example.com/jobs?id=123')
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()['details']['duplicate']['id'], job['id'])
        self.assertEqual(self.create(application_url='https://example.com/jobs?id=456').status_code, 201)

    def test_missing_url_or_same_title_is_not_a_duplicate(self):
        self.assertEqual(self.create().status_code, 201)
        self.assertEqual(self.create().status_code, 201)

    def test_import_duplicate_matches_existing_manual_job(self):
        saved = self.create(application_url='https://example.com/jobs/123').json()
        imported = self.import_email()
        self.assertEqual(imported['duplicate']['id'], saved['id'])
        response = self.create(import_id=imported['id'], application_url=imported['draft_data']['application_url'])
        self.assertEqual(response.status_code, 409)

    def test_owner_scoping_on_every_endpoint(self):
        source = self.import_email()
        saved = self.create(import_id=source['id']).json()
        with self.sessions() as db:
            db.add(User(name='Other',email='other@example.com',password_hash=self.password_hash)); db.commit()
        other = {'Authorization':f'Bearer {create_access_token(2)}'}
        for path in (f'/jobs/{saved["id"]}', f'/jobs/imports/{source["id"]}'):
            self.assertEqual(self.client.get(path,headers=other).status_code,404)
            self.assertEqual(self.client.get(path).status_code,401)
        self.assertEqual(self.client.post('/jobs',headers=other,json={'title':'Stolen','import_id':source['id']}).status_code,404)
        self.assertEqual(self.client.put(f'/jobs/{saved["id"]}',headers=other,json={'title':'Stolen','expected_revision':1}).status_code,404)
        self.assertEqual(self.client.get('/jobs',headers=other).json()['total'],0)
        self.assertEqual(self.client.get('/jobs/imports',headers=other).json()['total'],0)
        # Identical sources and URLs are allowed in different accounts.
        own_import = self.import_email(headers=other)
        self.assertNotEqual(own_import['id'],source['id'])
        self.assertEqual(self.client.post('/jobs',headers=other,json={'title':'Own','import_id':own_import['id']}).status_code,201)

    def test_authentication_for_lists_and_mutations(self):
        for path in ('/jobs','/jobs/imports'):
            self.assertEqual(self.client.get(path).status_code,401)
        for method,path,payload in [('post','/jobs',{'title':'Role'}),('post','/jobs/imports',{'raw_text':'Title: Role'}),('put','/jobs/1',{'title':'Role','expected_revision':1})]:
            self.assertEqual(getattr(self.client,method)(path,json=payload).status_code,401)

    def test_search_filters_pagination_and_literal_wildcards(self):
        a = self.create(title='100% Engineer',company='One',work_mode='remote').json()
        b = self.create(title='Designer',company='Two',work_mode='onsite').json()
        self.update(b,status='archived')
        self.create(title='Analyst',company='One')
        self.assertEqual(self.client.get('/jobs?q=one&status=saved',headers=self.headers).json()['total'],2)
        self.assertEqual(self.client.get('/jobs?q=%25',headers=self.headers).json()['total'],1)
        self.assertEqual(self.client.get('/jobs?work_mode=remote&source=manual',headers=self.headers).json()['items'][0]['id'],a['id'])
        first = self.client.get('/jobs?limit=1',headers=self.headers).json()
        second = self.client.get('/jobs?limit=1&offset=1',headers=self.headers).json()
        self.assertEqual(first['total'],3)
        self.assertNotEqual(first['items'][0]['id'],second['items'][0]['id'])
        self.assertEqual(self.client.get('/jobs?status=archived',headers=self.headers).json()['total'],1)
        for query in ('limit=0','offset=-1','work_mode=other','source=other','q='+'x'*201):
            self.assertEqual(self.client.get('/jobs?'+query,headers=self.headers).status_code,422)

    def test_pending_imports_reopen_and_preserve_whitespace(self):
        raw = '  Title: Engineer\r\n\r\n Company: Example  \n'
        imported = self.import_email(raw)
        self.assertEqual(imported['raw_text'],raw)
        pending = self.client.get('/jobs/imports',headers=self.headers).json()
        self.assertEqual(pending['items'][0]['id'],imported['id'])
        self.assertNotIn('raw_text',pending['items'][0])
        self.assertEqual(self.client.get(f'/jobs/imports/{imported["id"]}',headers=self.headers).json(),imported)

    def test_update_revision_and_source_immutability(self):
        source = self.import_email()
        job = self.create(import_id=source['id']).json()
        updated = self.update(job,title='Updated',status='archived')
        self.assertEqual(updated.status_code,200,updated.text)
        self.assertEqual(updated.json()['revision'],2)
        self.assertEqual(updated.json()['source']['raw_text'],self.source)
        self.assertEqual(self.update(job,title='Stale').status_code,409)
        self.assertEqual(self.update(updated.json(),status='saved').status_code,200)

    def test_updating_to_duplicate_url_does_not_mutate_job(self):
        self.create(application_url='https://example.com/1')
        other = self.create(application_url='https://example.com/2').json()
        self.assertEqual(self.update(other,application_url='https://example.com/1').status_code,409)
        self.assertEqual(self.client.get(f'/jobs/{other["id"]}',headers=self.headers).json(),other)

    def test_invalid_inputs_and_missing_records(self):
        for data in ({'title':''},{'title':'x'*256},{'title':'Valid','application_url':'javascript:x'}, {'title':'Valid','application_url':'https://user:pass@example.com'}, {'title':'Valid','skills':['x']*101}, {'title':'Valid','user_id':2}):
            self.assertEqual(self.client.post('/jobs',headers=self.headers,json=data).status_code,422)
        for source in (' ', 'x'*100001):
            self.assertEqual(self.client.post('/jobs/imports',headers=self.headers,json={'raw_text':source}).status_code,422)
        self.assertEqual(self.create(import_id=999).status_code,404)
        self.assertEqual(self.client.get('/jobs/999',headers=self.headers).status_code,404)
        self.assertEqual(self.client.get('/jobs/imports/999',headers=self.headers).status_code,404)

    def test_commit_failure_rolls_back(self):
        with patch('sqlalchemy.orm.Session.commit',side_effect=RuntimeError('private failure')):
            response=self.create()
        self.assertEqual(response.status_code,500)
        self.assertNotIn('private failure',response.text)
        self.assertEqual(self.client.get('/jobs',headers=self.headers).json()['total'],0)
