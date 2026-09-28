"""Confirmed profiles are isolated from parser output, other users, and stale editors."""
import copy
import unittest
from unittest.mock import patch
from sqlalchemy import select, func
import test_sprint1
from app.models.resume import Resume
from app.models.resume_parse import ResumeParse
from app.models.profile import Profile
from app.models.user import User
from app.utils.password import hash_password
from app.utils.jwt import create_access_token


class ProfileAPITests(unittest.TestCase):
    setUp = test_sprint1.SprintOneTests.setUp
    tearDown = test_sprint1.SprintOneTests.tearDown

    @classmethod
    def setUpClass(cls):
        cls.password_hash = hash_password('synthetic-password')

    def source(self, user_id=1, parse=True):
        with self.sessions() as db:
            row = Resume(user_id=user_id, file_name='profile.pdf', file_path='/synthetic.pdf', file_type='application/pdf', file_size=100, raw_text='Name: Original Name\nSKILLS\nPython, SQL')
            db.add(row); db.commit(); resume_id = row.id
        if parse:
            response = self.client.post(f'/resume/{resume_id}/parse', headers={'Authorization': f'Bearer {create_access_token(user_id)}'})
            self.assertEqual(response.status_code, 200, response.text)
        return resume_id

    def payload(self, resume_id, revision=0):
        return {'source_resume_id': resume_id, 'expected_revision': revision, 'data': {
            'contact': {'name': 'Reviewed Name', 'email': 'reviewed@example.com', 'links': ['https://example.com']},
            'summary': 'Reviewed summary', 'skills': ['Python', 'React'],
            'experience': [{'title': 'Engineer', 'company': 'Example', 'date_text': '2023 – Present', 'description': ['Built tools']}],
            'education': [{'degree': 'BSc', 'institution': 'Example University'}],
            'projects': [{'name': 'JobPilot', 'technologies': ['Python'], 'links': ['https://example.com/project']}],
        }}

    def test_create_and_reload_preserves_source_draft_and_account(self):
        resume_id = self.source()
        before = self.client.get(f'/resume/{resume_id}/parse', headers=self.headers).json()
        result = self.client.put('/profile', headers=self.headers, json=self.payload(resume_id))
        self.assertEqual(result.status_code, 200, result.text)
        body = result.json()
        self.assertEqual(body['revision'], 1)
        self.assertEqual(body['source_parser_version'], 'rules-v3')
        self.assertEqual(body['data']['contact']['name'], 'Reviewed Name')
        self.assertEqual(self.client.get('/profile', headers=self.headers).json(), body)
        self.assertEqual(self.client.get(f'/resume/{resume_id}/parse', headers=self.headers).json(), before)
        with self.sessions() as db:
            self.assertIn('Original Name', db.get(Resume, resume_id).raw_text)
            self.assertEqual(db.get(User, 1).email, 'alex@example.com')
            self.assertEqual(db.scalar(select(func.count()).select_from(Profile)), 1)

    def test_reparse_never_overwrites_confirmed_profile(self):
        resume_id = self.source()
        saved = self.client.put('/profile', headers=self.headers, json=self.payload(resume_id)).json()
        self.client.post(f'/resume/{resume_id}/parse?force=true', headers=self.headers)
        self.assertEqual(self.client.get('/profile', headers=self.headers).json(), saved)
        # Existing confirmed data remains editable even after a later parser failure.
        with self.sessions() as db:
            row = db.scalar(select(ResumeParse)); row.status = 'failed'; row.draft_data = None; db.commit()
        response = self.client.put('/profile', headers=self.headers, json=self.payload(resume_id, 1))
        self.assertEqual(response.status_code, 200, response.text)

    def test_update_and_remove_entries_keeps_one_profile(self):
        resume_id = self.source()
        original = self.client.put('/profile', headers=self.headers, json=self.payload(resume_id)).json()
        payload = self.payload(resume_id, 1)
        payload['data']['experience'] = []
        payload['data']['skills'] = ['Rust']
        result = self.client.put('/profile', headers=self.headers, json=payload).json()
        self.assertEqual(result['revision'], 2)
        self.assertEqual(result['id'], original['id'])
        self.assertEqual(result['created_at'], original['created_at'])
        self.assertEqual(result['data']['experience'], [])
        self.assertEqual(result['data']['skills'], ['Rust'])

    def test_stale_create_and_update_rejected_without_changes(self):
        resume_id = self.source()
        self.client.put('/profile', headers=self.headers, json=self.payload(resume_id))
        for stale in (0, 5):
            result = self.client.put('/profile', headers=self.headers, json=self.payload(resume_id, stale))
            self.assertEqual(result.status_code, 409)
        self.assertEqual(self.client.get('/profile', headers=self.headers).json()['revision'], 1)

    def test_authentication_and_owner_scoping(self):
        resume_id = self.source()
        with self.sessions() as db:
            db.add(User(name='Other', email='other@example.com', password_hash=self.password_hash)); db.commit()
        other_headers = {'Authorization': f'Bearer {create_access_token(2)}'}
        self.assertEqual(self.client.get('/profile').status_code, 401)
        self.assertEqual(self.client.put('/profile', json=self.payload(resume_id)).status_code, 401)
        self.assertEqual(self.client.get('/profile', headers=other_headers).status_code, 404)
        self.assertEqual(self.client.put('/profile', headers=other_headers, json=self.payload(resume_id)).status_code, 404)
        self.client.put('/profile', headers=self.headers, json=self.payload(resume_id))
        other_id = self.source(2)
        self.client.put('/profile', headers=other_headers, json=self.payload(other_id))
        self.assertEqual(self.client.get('/profile', headers=self.headers).json()['source_resume_id'], resume_id)
        self.assertEqual(self.client.get('/profile', headers=other_headers).json()['source_resume_id'], other_id)

    def test_missing_and_unparsed_sources(self):
        self.assertEqual(self.client.get('/profile', headers=self.headers).status_code, 404)
        for resume_id, expected in [(999, 404), (self.source(parse=False), 409), (None, 422)]:
            self.assertEqual(self.client.put('/profile', headers=self.headers, json=self.payload(resume_id)).status_code, expected)

    def test_switch_source_requires_completed_owned_draft(self):
        first_id = self.source()
        self.client.put('/profile', headers=self.headers, json=self.payload(first_id))
        next_id = self.source(parse=False)
        self.assertEqual(self.client.put('/profile', headers=self.headers, json=self.payload(next_id, 1)).status_code, 409)
        self.client.post(f'/resume/{next_id}/parse', headers=self.headers)
        result = self.client.put('/profile', headers=self.headers, json=self.payload(next_id, 1))
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()['source_resume_id'], next_id)
        self.assertEqual(result.json()['revision'], 2)

    def test_blank_optional_fields_stay_null_and_unknown_fields_rejected(self):
        resume_id = self.source()
        payload = self.payload(resume_id)
        payload['data']['contact'] = {'name': '  Reviewed Name  ', 'email': '   ', 'phone': ''}
        payload['data']['education'] = [{'degree': ''}]
        result = self.client.put('/profile', headers=self.headers, json=payload)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertIsNone(result.json()['data']['contact']['email'])
        self.assertEqual(result.json()['data']['contact']['name'], 'Reviewed Name')
        self.assertIsNone(result.json()['data']['education'][0]['degree'])
        payload['expected_revision'] = 1
        payload['data']['experience'][0]['source_text'] = 'attempted source edit'
        self.assertEqual(self.client.put('/profile', headers=self.headers, json=payload).status_code, 422)

    def test_validation_rejects_bad_email_links_oversize_and_empty_profile(self):
        resume_id = self.source()
        base = self.payload(resume_id)
        invalid_data = [
            {'contact': {'email': 'bad-email'}},
            {'contact': {'links': ['javascript:alert(1)']}},
            {'projects': [{'links': ['https://user:secret@example.com']}]},
            {'summary': 'a' * 5001}, {'skills': ['x'] * 201},
            {'experience': [{}] * 51}, {'skills': [' ']}, {},
            {'experience': [{}]}, {'user_id': 2},
        ]
        for data in invalid_data:
            with self.subTest(data=str(data)[:70]):
                payload = copy.deepcopy(base); payload['data'] = data
                self.assertEqual(self.client.put('/profile', headers=self.headers, json=payload).status_code, 422)
        with self.sessions() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Profile)), 0)

    def test_commit_failure_rolls_back_existing_profile(self):
        resume_id = self.source()
        saved = self.client.put('/profile', headers=self.headers, json=self.payload(resume_id)).json()
        with patch('sqlalchemy.orm.Session.commit', side_effect=RuntimeError('private details')):
            response = self.client.put('/profile', headers=self.headers, json=self.payload(resume_id, 1))
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('private details', response.text)
        self.assertEqual(self.client.get('/profile', headers=self.headers).json(), saved)

    def test_deleting_source_preserves_confirmed_data(self):
        resume_id = self.source()
        saved = self.client.put('/profile', headers=self.headers, json=self.payload(resume_id)).json()
        with self.sessions() as db:
            db.delete(db.get(Resume, resume_id)); db.commit()
        response = self.client.get('/profile', headers=self.headers).json()
        self.assertEqual(response['data'], saved['data'])
        self.assertIsNone(response['source_resume_id'])
        self.assertEqual(self.client.put('/profile', headers=self.headers, json=self.payload(None, 1)).status_code, 200)
