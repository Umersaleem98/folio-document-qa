from pathlib import Path
import pymupdf
from .config import settings


def file_path(document_id):
    # IDs are generated internally; never use original filenames as storage paths.
    import uuid
    uuid.UUID(document_id)
    return settings.storage_dir / 'uploads' / f'{document_id}.pdf'


def extract_chunks(path: Path):
    chunks = []
    total = 0
    with pymupdf.open(path) as pdf:
        if not pdf.is_pdf or pdf.needs_pass:
            raise ValueError('Encrypted or invalid PDFs are unsupported')
        if not 1 <= len(pdf) <= settings.max_pdf_pages:
            raise ValueError('PDF exceeds page limit')
        pages = len(pdf)
        for page_number, page in enumerate(pdf, start=1):
            text = page.get_text('text').replace('\x00', '').strip()
            total += len(text)
            if total > settings.max_extracted_characters:
                raise ValueError('PDF exceeds extracted text limit')
            # Page-local chunks preserve accurate citations; 200-character overlap.
            for start in range(0, len(text), 1000):
                part = text[start:start + 1200].strip()
                if len(part) >= 20:
                    chunks.append({'page': page_number, 'text': part})
    if not chunks:
        raise ValueError('No extractable text. Scanned PDFs require OCR before upload.')
    return pages, chunks
