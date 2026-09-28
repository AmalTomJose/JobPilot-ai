import re
import pymupdf

from app.middlewares.exception_middleware import UserException


class PDFService:
    @staticmethod
    def page_text(page) -> str:
        """Read visual lines, separating clear side-by-side columns.

        PDF content-stream order is often unrelated to the order a person reads.
        Ambiguous layouts fall back to visual top-to-bottom order, not guessed text.
        """
        lines = []
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines', []):
                text = ''.join(span['text'] for span in line['spans']).strip()
                if text:
                    lines.append((*line['bbox'], text))
        if not lines:
            return ''

        def render(items):
            result, previous = [], None
            for item in sorted(items, key=lambda row: (round(row[1], 1), row[0])):
                if previous and item[1] - previous[3] > max(6, (previous[3] - previous[1]) * .7):
                    result.append('')
                result.append(item[4])
                previous = item
            return '\n'.join(result)

        starts = sorted(set(round(line[0]) for line in lines))
        candidates = []
        for left_start, right_start in zip(starts, starts[1:]):
            if right_start - left_start < page.rect.width * .18:
                continue
            right = [line for line in lines if line[0] >= right_start - 1]
            left = [line for line in lines if line[2] < right_start - 12]
            spanning = [line for line in lines if line not in left and line not in right]
            # A right-aligned date column is part of the main text, not a sidebar.
            right_prose = [line for line in right if len(re.findall(r'[A-Za-z]{3,}', line[4])) >= 2
                           and not re.search(r'\b(?:19|20)\d{2}\b', line[4])]
            if len(left) >= 3 and len(right) >= 3 and len(right_prose) >= 2 and len(spanning) <= max(2, len(lines) * .2):
                candidates.append((len(left) + len(right), left, right, spanning))
        if not candidates:
            return render(lines)
        _, left, right, spanning = max(candidates, key=lambda item: item[0])
        result = []
        # Full-width headings divide the page into independently ordered bands.
        for boundary in sorted(spanning, key=lambda line: line[1]):
            for column in (left, right):
                before = [line for line in column if line[1] < boundary[1]]
                if before:
                    result.append(render(before))
                    column[:] = [line for line in column if line not in before]
            result.append(boundary[4])
        result.extend(render(column) for column in (left, right) if column)
        return '\n\n'.join(result)

    @staticmethod
    def extract_text(file_path: str) -> str:
        try:
            with pymupdf.open(file_path) as document:
                if not document.is_pdf:
                    raise UserException(400, "The uploaded file is not a valid PDF")
                if document.needs_pass:
                    raise UserException(400, "Please upload a PDF without password protection")
                pages = []
                for page in document:
                    extracted = PDFService.page_text(page)
                    if not extracted.strip() and page.get_images():
                        raise UserException(422, 'A page contains images but no readable text. Export a text-based PDF or run OCR before uploading; image-only pages cannot be extracted yet')
                    pages.append(extracted)
                text = "\n\n".join(pages).strip()
        except (pymupdf.FileDataError, pymupdf.EmptyFileError, RuntimeError) as error:
            raise UserException(400, "This PDF could not be read. Try exporting it again") from error
        if not text:
            raise UserException(422, "No text found. Upload a text-based PDF; scanned images are not supported yet")
        return text
