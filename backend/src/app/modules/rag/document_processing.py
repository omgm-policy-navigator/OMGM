from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse


class DocumentProcessingError(ValueError):
    """Raised when a source document cannot produce safe RAG chunks."""


class DocumentType(StrEnum):
    OVERVIEW = "OVERVIEW"
    OFFICIAL_NOTICE = "OFFICIAL_NOTICE"
    APPLICATION_GUIDE = "APPLICATION_GUIDE"
    FAQ = "FAQ"


class ChunkKind(StrEnum):
    OVERVIEW = "OVERVIEW"
    ELIGIBILITY = "ELIGIBILITY"
    BENEFIT = "BENEFIT"
    APPLICATION_PERIOD = "APPLICATION_PERIOD"
    APPLICATION_METHOD = "APPLICATION_METHOD"
    REQUIRED_DOCUMENTS = "REQUIRED_DOCUMENTS"
    CONTACT = "CONTACT"
    TABLE_ROW = "TABLE_ROW"
    OTHER = "OTHER"


class ChunkQuality(StrEnum):
    APPROVED = "APPROVED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True)
class SourceDocument:
    document_id: str
    policy_id: str
    title: str
    content: str
    source_url: str
    document_type: DocumentType | None = None

    def __post_init__(self) -> None:
        for field_name in ("document_id", "policy_id", "title", "content"):
            if not getattr(self, field_name).strip():
                raise DocumentProcessingError(f"{field_name} must not be blank")
        parsed = urlparse(self.source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise DocumentProcessingError("source_url must be an absolute HTTP(S) URL")


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    document_id: str
    policy_id: str
    document_type: DocumentType
    chunk_kind: ChunkKind
    heading: str
    content: str
    source_url: str
    source_location: str
    quality: ChunkQuality
    quality_issues: tuple[str, ...]
    content_hash: str


@dataclass(frozen=True)
class EmbeddingSeed:
    chunk_id: str
    policy_id: str
    document_id: str
    document_type: DocumentType
    chunk_kind: ChunkKind
    heading: str
    content: str
    source_url: str
    source_location: str
    content_hash: str


_HEADING = re.compile(r"^(?:#{1,6}\s+)(.+)$")
_ARTICLE = re.compile(r"^(제\s*\d+\s*조(?:의\s*\d+)?(?:\s*\([^)]*\))?)\s*(.*)$")
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?。])\s+")
_TABLE_SEPARATOR = re.compile(r"^:?-{3,}:?$")
_TABLE_CELL_SPLIT = re.compile(r"(?<!\\)\|")
_PHONE_PATTERN = re.compile(r"(?<!\d)(?:0\d{1,2}[-.\s]?)?\d{3,4}[-.\s]?\d{4}(?!\d)")
_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

_KIND_CUES: tuple[tuple[ChunkKind, tuple[str, ...]], ...] = (
    (ChunkKind.REQUIRED_DOCUMENTS, ("제출서류", "구비서류", "필요서류", "첨부서류")),
    (ChunkKind.APPLICATION_METHOD, ("신청방법", "신청 방법", "접수방법", "접수처", "온라인 신청")),
    (ChunkKind.APPLICATION_PERIOD, ("신청기간", "신청 기간", "접수기간", "모집기간")),
    (ChunkKind.ELIGIBILITY, ("신청대상", "신청 대상", "지원대상", "지원 대상", "자격", "요건")),
    (ChunkKind.BENEFIT, ("지원내용", "지원 내용", "지원금액", "혜택", "지급")),
    (ChunkKind.CONTACT, ("문의", "연락처", "담당부서")),
)


def classify_document_type(title: str, content: str = "") -> DocumentType:
    combined = f"{title} {content[:200]}".casefold()
    if "faq" in combined or "자주 묻는" in combined:
        return DocumentType.FAQ
    if "공고" in combined or "고시" in combined:
        return DocumentType.OFFICIAL_NOTICE
    if "신청 안내" in combined or "이용 안내" in combined or "가이드" in combined:
        return DocumentType.APPLICATION_GUIDE
    return DocumentType.OVERVIEW


def process_document(document: SourceDocument) -> tuple[DocumentChunk, ...]:
    document_type = document.document_type or classify_document_type(document.title, document.content)
    chunks: list[DocumentChunk] = []
    heading = document.title.strip()
    paragraph_lines: list[str] = []
    paragraph_number = 0
    table_number = 0
    lines = document.content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    index = 0

    def flush_paragraph() -> None:
        nonlocal paragraph_number
        text = " ".join(line.strip() for line in paragraph_lines if line.strip())
        paragraph_lines.clear()
        if not text:
            return
        paragraph_number += 1
        for sentence_number, sentence in enumerate(_semantic_segments(text), start=1):
            location = f"heading:{heading}/paragraph:{paragraph_number}/segment:{sentence_number}"
            chunks.append(_make_chunk(document, document_type, heading, sentence, location))

    while index < len(lines):
        line = lines[index].strip()
        if not line:
            flush_paragraph()
            index += 1
            continue

        heading_match = _HEADING.match(line)
        article_match = _ARTICLE.match(line)
        if heading_match or article_match:
            flush_paragraph()
            if heading_match:
                heading = heading_match.group(1).strip()
            elif article_match:
                heading = article_match.group(1).strip()
                remainder = article_match.group(2).strip()
                if remainder:
                    paragraph_lines.append(remainder)
            index += 1
            continue

        if _is_table_line(line):
            flush_paragraph()
            table_lines: list[str] = []
            while index < len(lines) and _is_table_line(lines[index].strip()):
                table_lines.append(lines[index].strip())
                index += 1
            table_number += 1
            chunks.extend(_table_chunks(document, document_type, heading, table_lines, table_number))
            continue

        paragraph_lines.append(line)
        index += 1

    flush_paragraph()
    if not chunks:
        raise DocumentProcessingError("document did not produce any chunks")
    return tuple(chunks)


def build_embedding_seed(chunks: tuple[DocumentChunk, ...]) -> tuple[EmbeddingSeed, ...]:
    return tuple(
        EmbeddingSeed(
            chunk_id=chunk.chunk_id,
            policy_id=chunk.policy_id,
            document_id=chunk.document_id,
            document_type=chunk.document_type,
            chunk_kind=chunk.chunk_kind,
            heading=chunk.heading,
            content=chunk.content,
            source_url=chunk.source_url,
            source_location=chunk.source_location,
            content_hash=chunk.content_hash,
        )
        for chunk in chunks
        if chunk.quality is ChunkQuality.APPROVED
    )


def _semantic_segments(text: str) -> tuple[str, ...]:
    sentences = tuple(part.strip() for part in _SENTENCE_BOUNDARY.split(text) if part.strip())
    if len(sentences) <= 1:
        return sentences or (text.strip(),)

    segments: list[str] = []
    current: list[str] = []
    current_kind: ChunkKind | None = None
    for sentence in sentences:
        kind = _classify_chunk_kind(sentence)
        if current and kind is not current_kind:
            segments.append(" ".join(current))
            current = []
        current.append(sentence)
        current_kind = kind
    if current:
        segments.append(" ".join(current))
    return tuple(segments)


def _make_chunk(
    document: SourceDocument,
    document_type: DocumentType,
    heading: str,
    content: str,
    source_location: str,
    *,
    forced_kind: ChunkKind | None = None,
    additional_issues: tuple[str, ...] = (),
) -> DocumentChunk:
    kind = forced_kind or _classify_chunk_kind(f"{heading} {content}")
    issues = tuple(
        dict.fromkeys(
            (
                *_quality_issues(
                    heading=heading,
                    content=content,
                    kind=kind,
                    source_location=source_location,
                ),
                *additional_issues,
            )
        )
    )
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    chunk_key = f"{document.document_id}|{source_location}|{digest}"
    chunk_id = f"chunk_{hashlib.sha256(chunk_key.encode('utf-8')).hexdigest()[:20]}"
    return DocumentChunk(
        chunk_id=chunk_id,
        document_id=document.document_id,
        policy_id=document.policy_id,
        document_type=document_type,
        chunk_kind=kind,
        heading=heading,
        content=content,
        source_url=document.source_url,
        source_location=source_location,
        quality=ChunkQuality.REVIEW_REQUIRED if issues else ChunkQuality.APPROVED,
        quality_issues=issues,
        content_hash=digest,
    )


def _quality_issues(
    *,
    heading: str,
    content: str,
    kind: ChunkKind,
    source_location: str,
) -> tuple[str, ...]:
    issues: list[str] = []
    semantic_text = f"{heading} {content}"
    detected_kinds = {
        candidate for candidate, cues in _KIND_CUES if any(cue in semantic_text for cue in cues)
    }
    if len(detected_kinds) > 1:
        issues.append("mixed_semantic_kinds")
    if len(content) > 1000:
        issues.append("chunk_too_long")
    if not source_location.strip():
        issues.append("missing_source_location")
    if (
        kind is ChunkKind.CONTACT
        or ChunkKind.CONTACT in detected_kinds
        or _contains_contact_information(content)
    ):
        issues.append("contact_requires_review")
    if kind is ChunkKind.OTHER and len(content) < 10:
        issues.append("insufficient_context")
    return tuple(issues)


def _classify_chunk_kind(text: str) -> ChunkKind:
    for kind, cues in _KIND_CUES:
        if any(cue in text for cue in cues):
            return kind
    return ChunkKind.OVERVIEW


def _is_table_line(line: str) -> bool:
    return line.startswith("|") and line.endswith("|") and line.count("|") >= 3


def _table_chunks(
    document: SourceDocument,
    document_type: DocumentType,
    heading: str,
    lines: list[str],
    table_number: int,
) -> tuple[DocumentChunk, ...]:
    rows = [_parse_table_row(line) for line in lines]
    if len(rows) < 2:
        return (
            _make_chunk(
                document,
                document_type,
                heading,
                lines[0],
                f"heading:{heading}/table:{table_number}",
                forced_kind=ChunkKind.TABLE_ROW,
            ),
        )
    headers = rows[0]
    data_rows = rows[1:]
    if all(_TABLE_SEPARATOR.fullmatch(cell) for cell in data_rows[0]):
        data_rows = data_rows[1:]
    chunks: list[DocumentChunk] = []
    for row_number, row in enumerate(data_rows, start=1):
        if len(row) != len(headers):
            content = " | ".join(row)
            additional_issues = ("table_column_mismatch",)
        else:
            content = "; ".join(f"{header}: {value}" for header, value in zip(headers, row, strict=True))
            additional_issues = ()
        chunks.append(
            _make_chunk(
                document,
                document_type,
                heading,
                content,
                f"heading:{heading}/table:{table_number}/row:{row_number}",
                forced_kind=ChunkKind.TABLE_ROW,
                additional_issues=additional_issues,
            )
        )
    return tuple(chunks)


def _parse_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|") and not stripped.endswith(r"\|"):
        stripped = stripped[:-1]
    return [cell.replace(r"\|", "|").strip() for cell in _TABLE_CELL_SPLIT.split(stripped)]


def _contains_contact_information(content: str) -> bool:
    return bool(_PHONE_PATTERN.search(content) or _EMAIL_PATTERN.search(content))
