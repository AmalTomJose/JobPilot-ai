import pymupdf

from app.middlewares.exception_middleware import UserException


class PDFService:
    @staticmethod
    def extract_text(file_path: str) -> str:
        try:
            with pymupdf.open(file_path) as document:
                if not document.is_pdf:
                    raise UserException(400, "The uploaded file is not a valid PDF")
                if document.needs_pass:
                    raise UserException(400, "Please upload a PDF without password protection")
                text = "\n".join(page.get_text() for page in document).strip()
        except (pymupdf.FileDataError, pymupdf.EmptyFileError, RuntimeError) as error:
            raise UserException(400, "This PDF could not be read. Try exporting it again") from error
        if not text:
            raise UserException(422, "No text found. Upload a text-based PDF; scanned images are not supported yet")
        return text
