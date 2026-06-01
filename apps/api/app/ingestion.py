
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from sqlmodel import Session, select

from .models import ReviewStatus, SourceDocument


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()


def ingest_file(session: Session, child_id: str, path: Path, storage_root: Path) -> SourceDocument:
    digest = sha256_file(path)
    existing = session.exec(select(SourceDocument).where(SourceDocument.sha256 == digest)).first()
    target_dir = storage_root / child_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / path.name
    if not target_path.exists():
        shutil.copy2(path, target_path)
    status = ReviewStatus.DUPLICATE if existing else ReviewStatus.NEW
    doc = SourceDocument(
        id=f'UP-{digest[:12]}',
        child_id=child_id,
        relative_path=str(target_path.relative_to(storage_root)),
        file_name=path.name,
        sha256=digest,
        bytes=path.stat().st_size,
        pages=0,
        text_chars=0,
        status=status,
        duplicate_of=existing.id if existing else None,
        duplicate_reason='exact sha256 match' if existing else None,
    )
    if session.get(SourceDocument, doc.id) is None:
        session.add(doc)
        session.commit()
        session.refresh(doc)
    return doc


def likely_duplicate_reason(text_a: str, text_b: str) -> str | None:
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a or not words_b:
        return None
    similarity = len(words_a & words_b) / len(words_a | words_b)
    return f'normalized text similarity {similarity:.2f}' if similarity >= 0.82 else None


def extract_text_locally(path: Path) -> dict[str, object]:
    # Local deterministic text route. Scanned PDFs are marked for OCR; runtime never calls a cloud API.
    if path.suffix.lower() not in {'.pdf', '.txt', '.md'}:
        return {'state': 'needs_ocr', 'method': 'local_tesseract_required', 'pages': [], 'quality': 0.0}
    try:
        text = path.read_text(errors='ignore')
    except UnicodeDecodeError:
        return {'state': 'needs_ocr', 'method': 'local_tesseract_required', 'pages': [], 'quality': 0.0}
    pages = text.split('--- PAGE') if '--- PAGE' in text else [text]
    quality = min(1.0, max(0.1, len(text.strip()) / 1000))
    return {'state': 'extracted', 'method': 'local_text', 'pages': pages, 'quality': quality}
