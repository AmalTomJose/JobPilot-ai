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


if __name__ == '__main__':
    unittest.main()
