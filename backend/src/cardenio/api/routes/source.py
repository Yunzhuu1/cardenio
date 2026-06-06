"""Source (novel import) API (api.md §4, API-3~6).

M1-T1: chapter input (paste/type) — done
M1-T2: file import (TXT / DOCX) — current
M1-T3: chapter segmentation — done
M1-T4: threshold check — done
M1-T5: text cleaning — current
"""

from __future__ import annotations

import io
import re

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from cardenio.api.deps import get_artifact_store
from cardenio.domain.models.source import (
    Chapter,
    CreateChapterRequest,
    SourceParagraph,
    SourceStats,
)
from cardenio.storage.sqlite_store import SqliteArtifactStore

router = APIRouter(prefix="/projects/{project_id}/source")

ALLOWED_MIMES = {
    "text/plain": "txt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}


@router.post("/chapters", status_code=201)
async def create_chapter(
    project_id: str,
    body: CreateChapterRequest,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-3: Add a chapter — persists text and builds paragraph index."""
    proj = await store.get_project(project_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")

    existing = await store.list_chapters(project_id)
    order = len(existing) + 1 if not body.order else body.order

    cleaned_text = _clean_basic(body.text)
    raw_paragraphs = _split_paragraphs(cleaned_text)
    chapter_id = f"ch_{order}"
    paragraph_models: list[SourceParagraph] = []
    for idx, para_text in enumerate(raw_paragraphs):
        paragraph_models.append(SourceParagraph(index=idx + 1, text=para_text))

    await store.save_paragraphs(
        project_id=project_id,
        chapter_id=chapter_id,
        paragraphs=[p.model_dump(mode="json") for p in paragraph_models],
    )

    return {
        "id": chapter_id,
        "title": body.title,
        "order": order,
        "char_count": sum(len(p.text) for p in paragraph_models),
        "paragraphs": [p.model_dump(mode="json") for p in paragraph_models],
    }


@router.get("")
async def get_source(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-5: Get all chapters with paragraph index and threshold check."""
    proj = await store.get_project(project_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")

    chapters = await store.list_chapters(project_id)
    total_chars = sum(c["char_count"] for c in chapters)
    stats = SourceStats(chapter_count=len(chapters), char_count=total_chars)

    return {
        "chapters": chapters,
        "stats": stats.model_dump(mode="json"),
        "threshold": {"min_chapters": 3, "passed": stats.threshold_passed},
    }


@router.post("/import")
async def import_file(
    project_id: str,
    file: UploadFile,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-4: Import TXT/DOCX file with auto-chapter detection.

    Returns auto-segmented chapter preview for author review.
    Actual chapter persistence happens on confirmation (M1-T3).
    """
    proj = await store.get_project(project_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if file.content_type is None:
        raise HTTPException(status_code=400, detail="Unknown file type")

    raw_bytes = await file.read()

    try:
        text, warnings = _extract_text(raw_bytes, file.content_type, file.filename or "")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if not text.strip():
        raise HTTPException(status_code=400, detail="File contains no readable text")

    # Auto-detect chapter boundaries and produce preview
    chapters = _detect_chapters(text)

    return {
        "chapters": chapters,
        "warnings": warnings,
    }


@router.put("/chapters/{chapter_id}")
async def update_chapter(
    project_id: str,
    chapter_id: str,
    chapter: Chapter,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-6: Edit a chapter. (M1-T3)"""
    raise HTTPException(status_code=501, detail="Not yet implemented")


@router.delete("/chapters/{chapter_id}", status_code=204)
async def delete_chapter(
    project_id: str,
    chapter_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> None:
    """API-6: Delete a chapter. (M1-T3)"""
    raise HTTPException(status_code=501, detail="Not yet implemented")


@router.post("/chapters:resegment")
async def resegment_chapters(
    project_id: str,
    body: dict,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-6: Split or merge chapters (author decides). (M1-T3)"""
    raise HTTPException(status_code=501, detail="Not yet implemented")


# =============================================================================
# Text extraction — pluggable per format
# =============================================================================


def _extract_text(
    raw: bytes, mime: str, filename: str
) -> tuple[str, list[str]]:
    """Dispatch to the correct extractor based on MIME or file extension."""
    warnings: list[str] = []

    # Resolve format from MIME, fallback to extension
    ext = ALLOWED_MIMES.get(mime) or _ext_from_filename(filename)

    if ext == "txt":
        text = _extract_txt(raw)
    elif ext == "docx":
        text = _extract_docx(raw)
    else:
        supported = ", ".join(ALLOWED_MIMES.values())
        raise ValueError(
            f"Unsupported format: {ext or mime}. Supported: {supported}"
        )

    text = _clean_basic(text)

    return text, warnings


def _ext_from_filename(filename: str) -> str:
    """Guess file extension from filename."""
    if filename.lower().endswith(".txt"):
        return "txt"
    if filename.lower().endswith(".docx"):
        return "docx"
    return ""


def _extract_txt(raw: bytes) -> str:
    """Extract plain text from a TXT file."""
    for enc in ("utf-8", "gbk", "gb2312", "gb18030"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def _extract_docx(raw: bytes) -> str:
    """Extract text from a DOCX file using python-docx."""
    try:
        from docx import Document
    except ImportError:
        raise ValueError("python-docx is required for DOCX import") from None

    doc = Document(io.BytesIO(raw))
    paragraphs: list[str] = []
    for para in doc.paragraphs:
        if para.text.strip():
            paragraphs.append(para.text.strip())
    return "\n\n".join(paragraphs)


# =============================================================================
# Chapter auto-detection (FR-1.2)
# =============================================================================

_CHAPTER_PATTERNS = [
    # 第一章, 第二章, ...
    r"第[一二三四五六七八九十百千零\d]+[章节]",
    # Chapter 1, Chapter 2, ...
    r"chapter\s*\d+",
    # 卷一, 卷二, ...
    r"第[一二三四五六七八九十百千零\d]+卷",
]


def _detect_chapters(text: str) -> list[dict]:
    """Auto-detect chapter boundaries from raw text.

    Scans for chapter markers (第X章 / Chapter X / 第X卷).
    Returns a list of chapter objects ready for preview.
    Falls back to a single chapter if no markers found.
    """
    marker_re = re.compile("|".join(_CHAPTER_PATTERNS), re.IGNORECASE)

    lines = text.split("\n")
    chapter_starts: list[int] = []  # line indices where chapters begin

    for i, line in enumerate(lines):
        stripped = line.strip()
        if marker_re.search(stripped) and len(stripped) < 80:
            chapter_starts.append(i)

    if not chapter_starts:
        # No markers found — treat as single chapter
        total_chars = sum(len(ln.strip()) for ln in lines if ln.strip())
        return [{
            "title": "第一章",
            "char_count": total_chars,
            "paragraphs": [1, max(1, len(_split_paragraphs(text)))],
        }]

    chapters: list[dict] = []
    for idx, start_line in enumerate(chapter_starts):
        end_line = (
            chapter_starts[idx + 1] if idx + 1 < len(chapter_starts) else len(lines)
        )
        chapter_text = "\n".join(lines[start_line:end_line])
        paras = _split_paragraphs(chapter_text)

        # First line is the chapter title
        title = lines[start_line].strip()
        # If the title line also contains body text, keep only the title part
        if marker_re.search(title):
            title = title.split(" ")[0]  # 简化为仅取标记

        chapters.append({
            "title": title,
            "char_count": sum(len(p) for p in paras),
            "paragraphs": [1, max(1, len(paras))],
        })

    return [c for c in chapters if c["char_count"] > 0]


# =============================================================================
# M1-T5 — text cleaning (FR-1.4)
# =============================================================================


def _clean_basic(text: str) -> str:
    """Basic text cleaning.  M1-T5: preserves intentional whitespace.

    Steps (order matters):
    1. BOM removal
    2. CRLF / CR → LF
    3. Remove control chars except \n, \t
    4. Collapse 3+ consecutive newlines to 2 (keep paragraph breaks)
    5. Full-width → half-width for ASCII variants
    6. Strip trailing whitespace per line (keep leading indentation for prose)
    """
    # 1. Remove BOM
    text = text.lstrip("\ufeff")

    # 2. Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 3. Remove control characters except \n (0x0A) and \t (0x09)
    text = "".join(
        ch for ch in text
        if ch == "\n" or ch == "\t" or ord(ch) >= 0x20 or ch == "　"
    )

    # 4. Collapse 3+ consecutive newlines to 2 (preserve paragraph gaps)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 5. Full-width → half-width for ASCII variants. Non-ASCII Chinese
    # punctuation such as "。" and "《》" stays unchanged.
    text = _normalize_fullwidth_ascii(text)

    # 6. Strip trailing whitespace per line (preserve leading indent for prose)
    lines = text.split("\n")
    text = "\n".join(line.rstrip() for line in lines)

    return text


def _normalize_fullwidth_ascii(text: str) -> str:
    """Normalize full-width ASCII variants to their half-width forms."""
    chinese_punctuation = {
        "，",
        "。",
        "！",
        "？",
        "；",
        "：",
        "、",
        "（",
        "）",
        "《",
        "》",
        "〈",
        "〉",
        "【",
        "】",
        "“",
        "”",
        "‘",
        "’",
    }
    normalized: list[str] = []
    for ch in text:
        code = ord(ch)
        if ch == "　":
            normalized.append(" ")
        elif ch in chinese_punctuation:
            normalized.append(ch)
        elif 0xFF01 <= code <= 0xFF5E:
            normalized.append(chr(code - 0xFEE0))
        else:
            normalized.append(ch)
    return "".join(normalized)


def _split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs by double-newline."""
    blocks = text.strip().split("\n\n")
    return [b.strip() for b in blocks if b.strip()]
