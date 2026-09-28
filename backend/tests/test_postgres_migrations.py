"""Opt-in migration tests. Only a disposable loopback database named jobpilot_test is accepted."""
import os
from pathlib import Path
import subprocess
import sys
import unittest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from pwdlib import PasswordHash

TEST_URL = os.environ.get("JOBPILOT_TEST_DATABASE_URL")


@unittest.skipUnless(TEST_URL, "Set JOBPILOT_TEST_DATABASE_URL to a disposable jobpilot_test database")
class PostgresMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parsed = make_url(TEST_URL)
        if parsed.host not in {"127.0.0.1", "localhost"} or parsed.database != "jobpilot_test":
            raise RuntimeError("Migration tests only accept a local database named jobpilot_test")
        cls.engine = create_engine(TEST_URL)
        cls.backend_dir = Path(__file__).resolve().parents[1]

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def migrate(self, direction, target):
        env = {**os.environ, "DATABASE_URL":TEST_URL}
        result = subprocess.run([sys.executable,"-m","alembic",direction,target],
                                cwd=self.backend_dir,env=env,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def setUp(self):
        self.migrate("downgrade", "base")

    def tearDown(self):
        self.migrate("downgrade", "base")

    def test_empty_database_upgrade_and_full_downgrade(self):
        self.migrate("upgrade", "head")
        inspector = inspect(self.engine)
        self.assertIn("users", inspector.get_table_names())
        self.assertIn("resumes", inspector.get_table_names())
        self.assertIn("raw_text", {column['name'] for column in inspector.get_columns('resumes')})
        self.assertEqual(inspector.get_foreign_keys('resumes')[0]['name'], 'resumes_user_id_fkey')
        self.migrate("downgrade", "base")
        self.assertNotIn("users", inspect(self.engine).get_table_names())

    def test_populated_legacy_users_preserve_credentials_and_receive_timestamp(self):
        self.migrate("upgrade", "3af135758130")
        original_hash = PasswordHash.recommended().hash("synthetic-test-password")
        with self.engine.begin() as connection:
            connection.execute(text("INSERT INTO users(firstname,email,password) VALUES (:name,:email,:password)"),
                               {"name":"Migration Test","email":"migration@example.com","password":original_hash})
        self.migrate("upgrade", "head")
        with self.engine.connect() as connection:
            row = connection.execute(text("SELECT name,password_hash,created_at FROM users")).one()
            self.assertEqual(row.name,"Migration Test")
            self.assertEqual(row.password_hash,original_hash)
            self.assertIsNotNone(row.created_at)
        self.migrate("downgrade", "3af135758130")
        with self.engine.connect() as connection:
            row = connection.execute(text("SELECT firstname,password FROM users")).one()
            self.assertEqual(row.password,original_hash)
            self.assertEqual(row.firstname,"Migration Test")

    def test_downgrade_handles_previous_unnamed_postgres_foreign_key(self):
        self.migrate("upgrade", "head")
        # Simulate a database upgraded using the previous unnamed FK operation.
        with self.engine.begin() as connection:
            connection.execute(text("ALTER TABLE resumes DROP CONSTRAINT resumes_user_id_fkey"))
            connection.execute(text("ALTER TABLE resumes ADD FOREIGN KEY (user_id) REFERENCES users(id)"))
        self.migrate("downgrade", "03951cc2af7d")
        self.assertEqual(inspect(self.engine).get_foreign_keys('resumes'), [])


    def test_sprint2_jsonb_locking_and_preservation_of_existing_resume(self):
        from sqlalchemy.orm import Session
        from app.models.user import User  # Register the relationship target.
        from app.models.resume import Resume
        from app.models.resume_parse import ResumeParse
        from app.repositories.resume_parse_repository import ResumeParseRepository
        from app.services.resume_parse_service import ResumeParseService
        from app.middlewares.exception_middleware import UserException
        self.migrate("upgrade", "767a67c5e23e")
        source = "Name: Test Person\nSKILLS\nPython, SQL"
        with self.engine.begin() as connection:
            user_id = connection.scalar(text("INSERT INTO users(name,email,password_hash,created_at) VALUES ('Test','test@example.com','test-hash',now()) RETURNING id"))
            resume_id = connection.scalar(text("INSERT INTO resumes(user_id,file_name,file_path,file_type,file_size,raw_text,created_at) VALUES (:user_id,'test.pdf','test.pdf','application/pdf',10,:source,now()) RETURNING id"), {"user_id":user_id,"source":source})
        self.migrate("upgrade", "head")
        columns = {column['name']:column for column in inspect(self.engine).get_columns('resume_parses')}
        self.assertEqual(str(columns['draft_data']['type']), 'JSONB')
        # A parent lock also protects the first request, before a parse row exists.
        with self.engine.begin() as lock:
            lock.execute(text('SELECT id FROM resumes WHERE id=:id FOR UPDATE'), {'id':resume_id})
            with Session(self.engine, expire_on_commit=False) as session:
                with self.assertRaises(UserException) as caught:
                    ResumeParseService(ResumeParseRepository(session)).parse(resume_id, user_id)
                self.assertEqual(caught.exception.status_code, 409)
        with Session(self.engine, expire_on_commit=False) as session:
            service = ResumeParseService(ResumeParseRepository(session))
            result = service.parse(resume_id, user_id)
            self.assertEqual(result.status, 'completed')
            self.assertEqual(result.draft_data['skills'], ['Python','SQL'])
            self.assertEqual(service.parse(resume_id, user_id).id, result.id)
            self.assertEqual(session.get(Resume, resume_id).raw_text, source)
            from sqlalchemy import select, func
            self.assertEqual(session.scalar(select(func.count()).select_from(ResumeParse)), 1)
        self.migrate("downgrade", "767a67c5e23e")
        self.assertNotIn('resume_parses', inspect(self.engine).get_table_names())
        with self.engine.connect() as connection:
            self.assertEqual(connection.scalar(text('SELECT raw_text FROM resumes WHERE id=:id'), {'id':resume_id}), source)


    def test_sprint3_profile_jsonb_lock_revision_and_downgrade(self):
        from sqlalchemy.orm import Session
        from app.models.user import User
        from app.models.resume import Resume
        from app.models.profile import Profile
        from app.repositories.resume_parse_repository import ResumeParseRepository
        from app.repositories.profile_repository import ProfileRepository
        from app.services.resume_parse_service import ResumeParseService
        from app.services.profile_service import ProfileService
        from app.schemas.profile import ProfileSave
        from app.middlewares.exception_middleware import UserException
        self.migrate('upgrade', 'b72e0f419ac3')
        source = 'Name: Before Review\nSKILLS\nPython'
        with self.engine.begin() as connection:
            user_id = connection.scalar(text("INSERT INTO users(name,email,password_hash,created_at) VALUES ('Test','profile@example.com','test-hash',now()) RETURNING id"))
            resume_id = connection.scalar(text("INSERT INTO resumes(user_id,file_name,file_path,file_type,file_size,raw_text,created_at) VALUES (:user_id,'test.pdf','test.pdf','application/pdf',10,:source,now()) RETURNING id"), {'user_id': user_id, 'source': source})
        with Session(self.engine, expire_on_commit=False) as db:
            ResumeParseService(ResumeParseRepository(db)).parse(resume_id, user_id)
        self.migrate('upgrade', 'head')
        columns = {column['name']: column for column in inspect(self.engine).get_columns('profiles')}
        self.assertEqual(str(columns['data']['type']), 'JSONB')
        request = ProfileSave(source_resume_id=resume_id, expected_revision=0, data={'contact': {'name': 'After Review'}, 'skills': ['Python', 'React']})
        with self.engine.begin() as lock:
            lock.execute(text('SELECT id FROM users WHERE id=:id FOR UPDATE'), {'id': user_id})
            with Session(self.engine) as db:
                with self.assertRaises(UserException) as caught:
                    ProfileService(ProfileRepository(db)).save(user_id, request)
                self.assertEqual(caught.exception.status_code, 409)
        with Session(self.engine, expire_on_commit=False) as db:
            service = ProfileService(ProfileRepository(db))
            result = service.save(user_id, request)
            self.assertEqual(result.data['contact']['name'], 'After Review')
            self.assertEqual(result.revision, 1)
            with self.assertRaises(UserException) as caught:
                service.save(user_id, request)
            self.assertEqual(caught.exception.status_code, 409)
            ResumeParseService(ResumeParseRepository(db)).parse(resume_id, user_id, force=True)
            self.assertEqual(service.get(user_id).data['contact']['name'], 'After Review')
            self.assertEqual(db.get(Resume, resume_id).raw_text, source)
        self.migrate('downgrade', 'b72e0f419ac3')
        self.assertNotIn('profiles', inspect(self.engine).get_table_names())
        with self.engine.connect() as connection:
            self.assertEqual(connection.scalar(text('SELECT raw_text FROM resumes WHERE id=:id'), {'id': resume_id}), source)
            self.assertEqual(connection.scalar(text('SELECT status FROM resume_parses WHERE resume_id=:id'), {'id': resume_id}), 'completed')


    def test_sprint4_imports_jobs_constraints_and_migration(self):
        from sqlalchemy.orm import Session
        from app.models.user import User
        from app.models.resume import Resume
        from app.models.job import Job, JobImport
        from app.repositories.job_repository import JobRepository
        from app.services.job_service import JobService
        from app.schemas.job import JobCreate
        from app.middlewares.exception_middleware import UserException
        from sqlalchemy.exc import IntegrityError
        self.migrate('upgrade', 'c83f1a520bd4')
        with self.engine.begin() as connection:
            user_id = connection.scalar(text("INSERT INTO users(name,email,password_hash,created_at) VALUES ('Job Tester','jobs@example.com','test-hash',now()) RETURNING id"))
        self.migrate('upgrade', 'head')
        columns = {column['name']: column for column in inspect(self.engine).get_columns('job_imports')}
        self.assertEqual(str(columns['draft_data']['type']), 'JSONB')
        with self.engine.begin() as lock:
            lock.execute(text('SELECT id FROM users WHERE id=:id FOR UPDATE'), {'id':user_id})
            with Session(self.engine) as db:
                with self.assertRaises(UserException) as caught:
                    JobService(JobRepository(db)).create(user_id, JobCreate(title='Locked'))
                self.assertEqual(caught.exception.status_code,409)
        with Session(self.engine,expire_on_commit=False) as db:
            service = JobService(JobRepository(db))
            imported = service.import_email(user_id,'Title: Engineer\nCompany: Example\nApply: https://example.com/jobs?id=1&utm_source=email')
            self.assertEqual(service.import_email(user_id,imported.raw_text).id,imported.id)
            job = service.create(user_id,JobCreate(title='Reviewed Engineer',import_id=imported.id,application_url=imported.draft_data.application_url))
            self.assertEqual(job.source.raw_text,imported.raw_text)
            with self.assertRaises(UserException):
                service.create(user_id,JobCreate(title='Duplicate',application_url='https://EXAMPLE.com:443/jobs?id=1#apply'))
            original = db.get(Job,job.id)
            db.add(Job(user_id=user_id,source_type='manual',title='Race',url_hash=original.url_hash,skills=[]))
            with self.assertRaises(IntegrityError): db.commit()
            db.rollback()
            self.assertEqual(service.repository.list(user_id)['total'],1)
        self.migrate('downgrade','c83f1a520bd4')
        self.assertNotIn('jobs',inspect(self.engine).get_table_names())
        with self.engine.connect() as connection:
            self.assertEqual(connection.scalar(text('SELECT name FROM users WHERE id=:id'),{'id':user_id}),'Job Tester')


    def test_sprint5_matching_migration_lock_and_preservation(self):
        from sqlalchemy.orm import Session
        from app.models.user import User
        from app.models.profile import Profile
        from app.models.job import Job
        from app.models.job_match import JobMatch
        from app.repositories.match_repository import MatchRepository
        from app.services.match_service import MatchService
        from app.middlewares.exception_middleware import UserException
        self.migrate('upgrade', 'd94a2b631ce5')
        with Session(self.engine, expire_on_commit=False) as db:
            user = User(name='Matching Test', email='matching@example.com', password_hash='test-hash')
            db.add(user); db.flush(); user_id = user.id
            profile = Profile(user_id=user_id, source_parser_version='test', revision=1, data={'skills': ['Python']})
            job = Job(user_id=user_id, source_type='manual', title='Test role', skills=['Python', 'SQL'])
            db.add_all([profile, job]); db.commit(); job_id = job.id
        self.migrate('upgrade', 'head')
        columns = {column['name']: column for column in inspect(self.engine).get_columns('job_matches')}
        self.assertEqual(str(columns['matched_skills']['type']), 'JSONB')
        with self.engine.begin() as lock:
            lock.execute(text('SELECT id FROM users WHERE id=:id FOR UPDATE'), {'id': user_id})
            with Session(self.engine) as db:
                with self.assertRaises(UserException) as caught:
                    MatchService(MatchRepository(db)).run(user_id)
                self.assertEqual(caught.exception.status_code, 409)
        with Session(self.engine, expire_on_commit=False) as db:
            service = MatchService(MatchRepository(db))
            self.assertEqual(service.run(user_id)['scored'], 1)
            self.assertEqual(service.list(user_id)['items'][0]['score'], 50)
            self.assertEqual(db.get(Job, job_id).revision, 1)
        self.migrate('downgrade', 'd94a2b631ce5')
        self.assertNotIn('job_matches', inspect(self.engine).get_table_names())
        with self.engine.connect() as connection:
            self.assertEqual(connection.scalar(text('SELECT title FROM jobs WHERE id=:id'), {'id': job_id}), 'Test role')


if __name__ == '__main__':
    unittest.main()
