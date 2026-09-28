import unittest
from unittest.mock import patch
from pathlib import Path
from sqlalchemy import select, func
import test_sprint1
from app.models.resume import Resume
from app.models.resume_parse import ResumeParse
from app.utils.password import hash_password
from app.utils.jwt import create_access_token
from app.services.resume_parser import parse_resume


class ParsingAPITests(unittest.TestCase):
    setUp = test_sprint1.SprintOneTests.setUp
    tearDown = test_sprint1.SprintOneTests.tearDown

    @classmethod
    def setUpClass(cls):
        cls.password_hash = hash_password('synthetic-password')

    def add_resume(self, text=None):
        source = (Path(__file__).parent / 'fixtures/resumes/standard.txt').read_text() if text is None else text
        with self.sessions() as db:
            row = Resume(user_id=1, file_name='sample.pdf', file_path='/private/sample.pdf', file_type='application/pdf', file_size=100, raw_text=source)
            db.add(row)
            db.commit()
            return row.id, source

    def test_parse_persists_draft_and_preserves_source(self):
        resume_id, source = self.add_resume()
        response = self.client.post(f'/resume/{resume_id}/parse', headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['draft_data']['contact']['name'], 'Alex Morgan')
        self.assertEqual(result['parser_version'], 'rules-v3')
        self.assertTrue(result['completed_at'])
        with self.sessions() as db:
            self.assertEqual(db.get(Resume, resume_id).raw_text, source)
            self.assertEqual(db.scalar(select(func.count()).select_from(ResumeParse)), 1)
        self.assertEqual(self.client.get(f'/resume/{resume_id}/parse', headers=self.headers).json(), result)

    def test_cache_and_force_keep_one_current_record(self):
        resume_id, _ = self.add_resume()
        first = self.client.post(f'/resume/{resume_id}/parse', headers=self.headers).json()
        with patch('app.services.resume_parse_service.parse_resume', wraps=parse_resume) as parser:
            self.assertEqual(self.client.post(f'/resume/{resume_id}/parse', headers=self.headers).json(), first)
            parser.assert_not_called()
            forced = self.client.post(f'/resume/{resume_id}/parse?force=true', headers=self.headers).json()
            parser.assert_called_once()
            self.assertEqual(forced['id'], first['id'])
        with self.sessions() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(ResumeParse)), 1)

    def test_source_or_version_change_invalidates_cache(self):
        resume_id, _ = self.add_resume()
        self.client.post(f'/resume/{resume_id}/parse', headers=self.headers)
        for change in ('version', 'source'):
            with self.sessions() as db:
                if change == 'version':
                    db.scalar(select(ResumeParse)).parser_version = 'older-rules'
                else:
                    db.get(Resume, resume_id).raw_text = 'SKILLS\nRust'
                db.commit()
            with patch('app.services.resume_parse_service.parse_resume', wraps=parse_resume) as parser:
                result = self.client.post(f'/resume/{resume_id}/parse', headers=self.headers)
                self.assertEqual(result.status_code, 200)
                parser.assert_called_once()
        self.assertEqual(result.json()['draft_data']['skills'], ['Rust'])

    def test_failure_is_saved_and_retry_succeeds(self):
        resume_id, source = self.add_resume()
        with patch('app.services.resume_parse_service.parse_resume', side_effect=RuntimeError('private internals')):
            result = self.client.post(f'/resume/{resume_id}/parse', headers=self.headers)
        self.assertEqual(result.json()['status'], 'failed')
        self.assertNotIn('private internals', result.text)
        self.assertIsNone(result.json()['draft_data'])
        self.assertEqual(self.client.get(f'/resume/{resume_id}/parse', headers=self.headers).json()['status'], 'failed')
        self.assertEqual(self.client.post(f'/resume/{resume_id}/parse', headers=self.headers).json()['status'], 'completed')
        with self.sessions() as db:
            self.assertEqual(db.get(Resume, resume_id).raw_text, source)

    def test_all_endpoints_enforce_owner_and_authentication(self):
        from app.models.user import User
        resume_id, _ = self.add_resume()
        self.client.post(f'/resume/{resume_id}/parse', headers=self.headers)
        with self.sessions() as db:
            db.add(User(name='Other User', email='other@example.com', password_hash=self.password_hash))
            db.commit()
        other = {'Authorization':f'Bearer {create_access_token(2)}'}
        for method, path in [('get',f'/resume/{resume_id}'), ('get',f'/resume/{resume_id}/parse'), ('post',f'/resume/{resume_id}/parse'), ('post',f'/resume/{resume_id}/parse?force=true')]:
            with self.subTest(path=path, method=method):
                self.assertEqual(getattr(self.client, method)(path, headers=other).status_code, 404)
                self.assertEqual(getattr(self.client, method)(path).status_code, 401)
        self.assertEqual(self.client.get('/resume', headers=other).json(), [])
        self.assertEqual(self.client.get('/resume').status_code, 401)

    def test_history_omits_text_and_storage_paths(self):
        resume_id, source = self.add_resume()
        detail = self.client.get(f'/resume/{resume_id}', headers=self.headers).json()
        self.assertEqual(detail['raw_text'], source)
        self.assertNotIn('file_path', detail)
        history = self.client.get('/resume', headers=self.headers).json()
        self.assertEqual(history[0]['id'], resume_id)
        self.assertNotIn('raw_text', history[0])
        self.assertNotIn('file_path', history[0])
        self.assertEqual(self.client.get('/resume?limit=0', headers=self.headers).status_code, 422)
        self.assertEqual(self.client.get('/resume?offset=1', headers=self.headers).json(), [])

    def test_missing_resume_and_missing_parse_return_404(self):
        resume_id, _ = self.add_resume()
        self.assertEqual(self.client.get(f'/resume/{resume_id}/parse', headers=self.headers).status_code, 404)
        self.assertEqual(self.client.get('/resume/999', headers=self.headers).status_code, 404)
        self.assertEqual(self.client.post('/resume/999/parse', headers=self.headers).status_code, 404)

    def test_invalid_text_does_not_create_record(self):
        for text, code in [(' \n ', 422), ('a'*200001, 413)]:
            resume_id, _ = self.add_resume(text)
            self.assertEqual(self.client.post(f'/resume/{resume_id}/parse', headers=self.headers).status_code, code)
        with self.sessions() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(ResumeParse)), 0)

    def test_ambiguous_text_completes_with_warnings_and_null_fields(self):
        resume_id, _ = self.add_resume('EXPERIENCE\nUnclear entry\nSomewhere')
        result = self.client.post(f'/resume/{resume_id}/parse', headers=self.headers).json()
        self.assertEqual(result['status'], 'completed')
        self.assertIsNone(result['draft_data']['experience'][0]['company'])
        self.assertIn('AMBIGUOUS_EXPERIENCE', [w['code'] for w in result['warnings']])

    def test_database_failure_rolls_back_parse(self):
        resume_id, source = self.add_resume()
        with patch('sqlalchemy.orm.Session.commit', side_effect=RuntimeError('database failure')):
            result = self.client.post(f'/resume/{resume_id}/parse', headers=self.headers)
        self.assertEqual(result.status_code, 500)
        with self.sessions() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(ResumeParse)), 0)
            self.assertEqual(db.get(Resume, resume_id).raw_text, source)
