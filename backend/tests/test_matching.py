import unittest
from unittest.mock import patch
from sqlalchemy import select, func
import test_sprint1
from app.models.profile import Profile
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.user import User
from app.services.skill_matcher import match_skills
from app.utils.password import hash_password
from app.utils.jwt import create_access_token


class SkillMatcherTests(unittest.TestCase):
    def test_coverage_aliases_and_evidence(self):
        result = match_skills(['python', 'Postgres'], ['Python', 'PostgreSQL', 'FastAPI'])
        self.assertEqual(result['score'], 66.7)
        self.assertEqual(result['missing_skills'], ['FastAPI'])
        self.assertEqual(result['matched_skills'][1], {'job_skill': 'PostgreSQL', 'profile_skill': 'Postgres'})

    def test_duplicates_do_not_inflate_score(self):
        self.assertEqual(match_skills(['React'], ['React', 'react.js', 'ReactJS', 'Python'])['score'], 50)

    def test_missing_data_is_not_zero(self):
        self.assertIsNone(match_skills([], ['Python'])['score'])
        self.assertIsNone(match_skills(['Python'], [])['score'])
        self.assertEqual(match_skills(['Python'], ['Java'])['score'], 0)

    def test_related_skills_are_not_equivalent(self):
        result = match_skills(['JavaScript', 'C++', 'AWS EC2', 'React'], ['Java', 'C', 'AWS', 'React Native'])
        self.assertEqual(result['score'], 0)
        self.assertEqual(len(result['missing_skills']), 4)

    def test_whitespace_unicode_and_blank_skills(self):
        self.assertEqual(match_skills([' Ｐｙｔｈｏｎ ', ''], ['python', ' '])['score'], 100)
        self.assertEqual(match_skills(['Microsoft   SQL Server'], ['MSSQL'])['score'], 100)


class MatchAPITests(unittest.TestCase):
    setUp = test_sprint1.SprintOneTests.setUp
    tearDown = test_sprint1.SprintOneTests.tearDown

    @classmethod
    def setUpClass(cls):
        cls.password_hash = hash_password('synthetic-match-test')

    def profile(self, skills=None, user_id=1):
        with self.sessions() as db:
            record = Profile(user_id=user_id, source_parser_version='test', revision=1, data={'skills': ['Python', 'Postgres'] if skills is None else skills})
            db.add(record); db.commit()
            return record.id

    def job(self, skills=None, status='saved', user_id=1):
        with self.sessions() as db:
            record = Job(user_id=user_id, source_type='manual', title='Synthetic role', skills=['Python', 'SQL'] if skills is None else skills, status=status)
            db.add(record); db.commit()
            return record.id

    def listing(self, query=''):
        response = self.client.get('/matches'+query, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def run_matches(self):
        response = self.client.post('/matches/run', headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_requires_authentication(self):
        self.assertEqual(self.client.get('/matches').status_code, 401)
        self.assertEqual(self.client.post('/matches/run').status_code, 401)

    def test_missing_profile_and_pending_job(self):
        self.job()
        page = self.listing()
        self.assertFalse(page['profile_ready'])
        self.assertEqual(page['pending'], 1)
        self.assertEqual(page['items'][0]['state'], 'pending')
        self.assertEqual(self.client.post('/matches/run', headers=self.headers).status_code, 409)

    def test_persists_results_ranks_and_reuses_rows(self):
        self.profile()
        low = self.job(['Java'])
        high = self.job(['Python', 'PostgreSQL'])
        mid = self.job(['Python', 'SQL'])
        self.assertEqual(self.run_matches()['scored'], 3)
        page = self.listing()
        self.assertEqual([item['job_id'] for item in page['items']], [high, mid, low])
        self.assertEqual([item['score'] for item in page['items']], [100, 50, 0])
        self.assertEqual(page['pending'], 0)
        self.run_matches()
        with self.sessions() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(JobMatch)), 3)

    def test_profile_job_and_rule_changes_mark_outdated(self):
        profile_id = self.profile()
        job_id = self.job()
        for change in ('profile', 'job', 'rules'):
            self.run_matches()
            with self.sessions() as db:
                if change == 'profile': db.get(Profile, profile_id).revision += 1
                elif change == 'job': db.get(Job, job_id).revision += 1
                else: db.scalar(select(JobMatch)).matcher_version = 'old-version'
                db.commit()
            self.assertEqual(self.listing()['outdated'], 1)
            self.assertEqual(self.listing()['items'][0]['state'], 'outdated')
        self.run_matches()
        self.assertEqual(self.listing()['outdated'], 0)

    def test_empty_skills_not_scored_or_claimed_missing(self):
        self.profile([])
        self.job(['Python'])
        self.assertEqual(self.run_matches()['insufficient'], 1)
        row = self.listing()['items'][0]
        self.assertIsNone(row['score'])
        self.assertEqual(row['reason'], 'profile_skills_missing')
        self.assertEqual(row['missing_skills'], [])

    def test_job_without_skills(self):
        self.profile()
        self.job([])
        self.run_matches()
        self.assertEqual(self.listing()['items'][0]['reason'], 'job_skills_missing')

    def test_archived_jobs_excluded_from_run_and_default_list(self):
        self.profile()
        self.job()
        self.job(status='archived')
        self.assertEqual(self.run_matches()['processed'], 1)
        self.assertEqual(self.listing()['total'], 1)
        all_jobs = self.listing('?include_archived=true')
        self.assertEqual(all_jobs['total'], 2)
        self.assertEqual(all_jobs['pending'], 1)

    def test_owner_isolation(self):
        with self.sessions() as db:
            other = User(name='Other', email='other@example.com', password_hash=self.password_hash)
            db.add(other); db.commit(); other_id = other.id
        self.profile(user_id=other_id)
        self.job(user_id=other_id)
        self.profile()
        own_id = self.job()
        self.assertEqual(self.run_matches()['processed'], 1)
        self.assertEqual([item['job_id'] for item in self.listing()['items']], [own_id])
        other_headers = {'Authorization': f'Bearer {create_access_token(other_id)}'}
        other_page = self.client.get('/matches', headers=other_headers).json()
        self.assertEqual(other_page['pending'], 1)
        self.assertIsNone(other_page['items'][0]['score'])

    def test_pagination_and_invalid_query(self):
        self.profile()
        for _ in range(3): self.job()
        self.run_matches()
        first = self.listing('?limit=1')
        second = self.listing('?limit=1&offset=1')
        self.assertEqual(first['total'], 3)
        self.assertNotEqual(first['items'][0]['job_id'], second['items'][0]['job_id'])
        for query in ('limit=0', 'offset=-1', 'limit=101'):
            self.assertEqual(self.client.get('/matches?'+query, headers=self.headers).status_code, 422)

    def test_transaction_failure_preserves_previous_result(self):
        self.profile()
        self.job()
        self.run_matches()
        before = self.listing()
        with patch('sqlalchemy.orm.Session.commit', side_effect=RuntimeError('private error')):
            result = self.client.post('/matches/run', headers=self.headers)
        self.assertEqual(result.status_code, 500)
        self.assertNotIn('private error', result.text)
        self.assertEqual(self.listing(), before)

    def test_matching_does_not_change_profile_or_job(self):
        profile_id = self.profile()
        job_id = self.job()
        self.run_matches()
        with self.sessions() as db:
            self.assertEqual(db.get(Profile, profile_id).data, {'skills': ['Python', 'Postgres']})
            self.assertEqual(db.get(Job, job_id).skills, ['Python', 'SQL'])
            self.assertEqual(db.get(Profile, profile_id).revision, 1)
            self.assertEqual(db.get(Job, job_id).revision, 1)
