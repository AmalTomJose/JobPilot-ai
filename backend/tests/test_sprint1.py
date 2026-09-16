"""Isolated regression tests: SQLite memory database and temporary PDF uploads."""
import io
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import pymupdf
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine, event, select, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.core.config import settings
from app.core.dependencies import get_db, get_resume_service
from app.database.base import Base
from app.models.user import User
from app.models.resume import Resume
from app.repositories.resume_repository import ResumeRepository
from app.repositories.user_repository import UserRepository
from app.services.resume_service import ResumeService, MAX_FILE_SIZE
from app.utils.password import hash_password, verify_password
from app.utils.jwt import create_access_token


def pdf_bytes(text="Alex Morgan\nPython developer", encrypted=False):
    with pymupdf.open() as document:
        page = document.new_page()
        if text:
            page.insert_text((60, 60), text)
        if encrypted:
            return document.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="secret")
        return document.tobytes()


class SprintOneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password = "test-password-123"
        cls.password_hash = hash_password(cls.password)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.upload_dir = Path(self.temp.name) / "uploads"
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, expire_on_commit=False)
        with self.sessions() as db:
            db.add(User(name="Alex Morgan", email="alex@example.com", password_hash=self.password_hash))
            db.commit()
        def test_db():
            with self.sessions() as db:
                yield db
        def test_service():
            with self.sessions() as db:
                yield ResumeService(ResumeRepository(db), self.upload_dir)
        app.dependency_overrides[get_db] = test_db
        app.dependency_overrides[get_resume_service] = test_service
        self.client = TestClient(app, raise_server_exceptions=False)
        self.headers = {"Authorization": f"Bearer {create_access_token(1)}"}

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.engine.dispose()
        self.temp.cleanup()

    def upload(self, data, mime="application/pdf", filename="resume.pdf"):
        return self.client.post("/resume/upload", headers=self.headers, files={"file":(filename,io.BytesIO(data),mime)})

    def assert_clean(self):
        with self.sessions() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Resume)), 0)
        self.assertEqual(list(self.upload_dir.glob("*.pdf")), [])

    def test_registration_hashes_password_and_returns_public_user(self):
        response = self.client.post("/auth/register", json={"name":"New Person","email":"new@example.com","password":self.password})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(set(response.json()["user"]), {"id","name","email"})
        with self.sessions() as db:
            user = db.scalar(select(User).where(User.email == "new@example.com"))
            self.assertNotEqual(user.password_hash, self.password)
            self.assertTrue(verify_password(self.password, user.password_hash))

    def test_duplicate_registration_is_conflict(self):
        response = self.client.post("/auth/register", json={"name":"Alex","email":"alex@example.com","password":self.password})
        self.assertEqual(response.status_code, 409)

    def test_repository_handles_duplicate_insert_race(self):
        from app.middlewares.exception_middleware import UserException
        with self.sessions() as db:
            with self.assertRaises(UserException) as caught:
                UserRepository(db).create("Alex", "alex@example.com", self.password_hash)
            self.assertEqual(caught.exception.status_code, 409)
            self.assertEqual(db.scalar(select(func.count()).select_from(User)), 1)

    def test_login_and_restore_user(self):
        response = self.client.post("/auth/login", json={"email":"alex@example.com","password":self.password})
        self.assertEqual(response.status_code, 200)
        restored = self.client.get("/auth/me", headers={"Authorization":f"Bearer {response.json()['access_token']}"})
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.json(), {"id":1,"name":"Alex Morgan","email":"alex@example.com"})

    def test_wrong_password_and_unknown_user_are_401(self):
        for email in ("alex@example.com", "missing@example.com"):
            with self.subTest(email=email):
                response = self.client.post("/auth/login", json={"email":email,"password":"wrong-password"})
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json()["message"], "Invalid email or password")

    def test_missing_and_malformed_tokens_are_401(self):
        for headers in ({}, {"Authorization":"Bearer broken"}, {"Authorization":"Basic invalid"}):
            with self.subTest(headers=headers):
                response = self.client.get("/auth/me", headers=headers)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.headers.get("www-authenticate"), "Bearer")

    def test_invalid_token_claims_are_401(self):
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        payloads = [{"sub":"1","exp":datetime.now(timezone.utc)-timedelta(hours=1)}, {"sub":"bad","exp":future}, {"sub":"-1","exp":future}, {"sub":"1"}, {"exp":future}, {"sub":"999","exp":future}]
        for payload in payloads:
            with self.subTest(payload=payload):
                token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
                self.assertEqual(self.client.get("/auth/me", headers={"Authorization":f"Bearer {token}"}).status_code, 401)

    def test_invalid_registration_is_422(self):
        response = self.client.post("/auth/register", json={"name":"A","email":"invalid","password":"x"})
        self.assertEqual(response.status_code, 422)
        self.assertIsInstance(response.json()["message"], str)

    def test_valid_upload_persists_file_text_and_owner(self):
        response = self.upload(pdf_bytes(), filename="../resume.pdf")
        self.assertEqual(response.status_code, 201, response.text)
        self.assertIn("Alex Morgan", response.json()["raw_text"])
        self.assertNotIn("file_path", response.json())
        with self.sessions() as db:
            resume = db.scalar(select(Resume))
            self.assertEqual(resume.user_id, 1)
            self.assertEqual(resume.file_name, "resume.pdf")
            self.assertIn("Python developer", resume.raw_text)
            self.assertTrue(Path(resume.file_path).is_file())
            self.assertEqual(Path(resume.file_path).parent, self.upload_dir)
            self.assertEqual(resume.file_size, Path(resume.file_path).stat().st_size)

    def test_upload_requires_authentication(self):
        response = self.client.post("/resume/upload", files={"file":("resume.pdf",pdf_bytes(),"application/pdf")})
        self.assertEqual(response.status_code, 401)
        self.assert_clean()

    def test_wrong_file_type_is_rejected(self):
        self.assertEqual(self.upload(b"text", mime="text/plain").status_code, 400)
        self.assert_clean()

    def test_empty_and_corrupt_files_are_cleaned_up(self):
        for data in (b"", b"not a PDF", b"%PDF-1.7\ncorrupted"):
            with self.subTest(data=data):
                self.assertEqual(self.upload(data).status_code, 400)
                self.assert_clean()

    def test_blank_pdf_is_rejected_with_useful_message(self):
        response = self.upload(pdf_bytes(text=""))
        self.assertEqual(response.status_code, 422)
        self.assertIn("No text", response.json()["message"])
        self.assert_clean()

    def test_password_protected_pdf_is_rejected(self):
        response = self.upload(pdf_bytes(encrypted=True))
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.json()["message"])
        self.assert_clean()

    def test_oversize_upload_is_rejected_and_cleaned_up(self):
        self.assertEqual(self.upload(b"x"*(MAX_FILE_SIZE+1)).status_code, 413)
        self.assert_clean()

    def test_long_filename_is_rejected(self):
        self.assertEqual(self.upload(pdf_bytes(), filename="a"*256+".pdf").status_code, 400)
        self.assert_clean()

    def test_database_failure_rolls_back_and_removes_file(self):
        with patch("sqlalchemy.orm.Session.commit", side_effect=RuntimeError("database unavailable")):
            response = self.upload(pdf_bytes())
        self.assertEqual(response.status_code, 500)
        self.assert_clean()

    def test_unexpected_extraction_failure_removes_file(self):
        with patch("app.services.resume_service.PDFService.extract_text", side_effect=RuntimeError("failure")):
            self.assertEqual(self.upload(pdf_bytes()).status_code, 500)
        self.assert_clean()

    def test_resume_repository_scopes_reads_to_owner(self):
        response = self.upload(pdf_bytes())
        self.assertEqual(response.status_code, 201)
        with self.sessions() as db:
            repository = ResumeRepository(db)
            self.assertIsNotNone(repository.get_by_id(response.json()["id"], 1))
            self.assertIsNone(repository.get_by_id(response.json()["id"], 2))
            self.assertEqual(repository.get_by_user_id(2), [])

    def test_cors_accepts_local_frontend_origins_only(self):
        for origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
            response = self.client.options("/resume/upload", headers={"Origin":origin,"Access-Control-Request-Method":"POST","Access-Control-Request-Headers":"authorization"})
            self.assertEqual(response.headers.get("access-control-allow-origin"), origin)
        response = self.client.options("/resume/upload", headers={"Origin":"https://untrusted.example","Access-Control-Request-Method":"POST"})
        self.assertNotIn("access-control-allow-origin", response.headers)

    def test_unrecognized_password_hash_does_not_crash(self):
        self.assertFalse(verify_password(self.password, "invalid-legacy-value"))

    def test_legacy_bcrypt_hash_is_supported(self):
        from pwdlib.hashers.bcrypt import BcryptHasher
        self.assertTrue(verify_password(self.password, BcryptHasher().hash(self.password)))


if __name__ == "__main__":
    unittest.main()
