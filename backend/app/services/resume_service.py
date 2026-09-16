from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.models.resume import Resume
from app.repositories.resume_repository import ResumeRepository
from app.middlewares.exception_middleware import UserException
from app.services.pdf_service import PDFService

MAX_FILE_SIZE = 5 * 1024 * 1024
CHUNK_SIZE = 64 * 1024


class ResumeService:
    def __init__(self, repository: ResumeRepository, upload_dir: Path | None = None):
        self.repository = repository
        self.upload_dir = upload_dir if upload_dir is not None else settings.UPLOAD_DIR

    def upload_resume(self, file: UploadFile, user_id: int) -> Resume:
        # This synchronous service runs in FastAPI's worker thread, not its event loop.
        path = None
        try:
            if file.content_type != "application/pdf":
                raise UserException(400, "Only PDF files are allowed")
            original_name = (file.filename or "resume.pdf").replace("\\", "/").rsplit("/", 1)[-1]
            original_name = original_name or "resume.pdf"
            if len(original_name) > 255:
                raise UserException(400, "The filename must be 255 characters or fewer")
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            path = self.upload_dir / f"{uuid4()}.pdf"
            size = 0
            with path.open("xb") as output:
                while chunk := file.file.read(CHUNK_SIZE):
                    size += len(chunk)
                    if size > MAX_FILE_SIZE:
                        raise UserException(413, "File size must be 5 MB or less")
                    output.write(chunk)
            if size == 0:
                raise UserException(400, "The PDF is empty. Please choose another file")
            raw_text = PDFService.extract_text(str(path))
            return self.repository.create(
                user_id=user_id, file_name=original_name, file_path=str(path),
                file_type="application/pdf", file_size=size, raw_text=raw_text,
            )
        except Exception:
            if path is not None:
                path.unlink(missing_ok=True)
            raise
        finally:
            file.file.close()
