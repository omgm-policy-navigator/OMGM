"""Raw policy source contract and deterministic storage naming rules."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import PurePosixPath
from urllib.parse import urlsplit


SCHEMA_VERSION = "1.0"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")


class SourceAuthority(StrEnum):
    """Whether evidence was published by an accountable policy authority."""

    OFFICIAL = "OFFICIAL"
    SECONDARY = "SECONDARY"


class SourceFormat(StrEnum):
    API_JSON = "API_JSON"
    HTML = "HTML"
    PDF = "PDF"
    DOCUMENT = "DOCUMENT"
    TEXT = "TEXT"


class RawPolicyStatus(StrEnum):
    COLLECTED = "COLLECTED"
    EXTRACTED = "EXTRACTED"
    REVIEWING = "REVIEWING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    OUTDATED = "OUTDATED"


def sha256_bytes(content: bytes) -> str:
    """Hash the exact bytes stored as the immutable original."""

    return hashlib.sha256(content).hexdigest()


def _require_utc(value: datetime, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError(f"{field_name} must be timezone-aware UTC")


def _validate_source_url(value: str) -> None:
    if not isinstance(value, str):
        raise TypeError("source_url must be a string")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("source_url must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password:
        raise ValueError("source_url must not contain credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("source_url must be canonical and contain no query or fragment")


@dataclass(frozen=True, slots=True)
class RawPolicyMetadata:
    """Sidecar metadata for one immutable raw policy source object."""

    collection_id: str
    raw_policy_id: str
    source_authority: SourceAuthority
    source_format: SourceFormat
    source_url: str
    publisher: str
    collected_at: datetime
    content_sha256: str
    media_type: str
    original_filename: str | None = None
    status: RawPolicyStatus = RawPolicyStatus.COLLECTED
    status_updated_at: datetime | None = None
    collector: str = "manual"
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.source_authority, SourceAuthority):
            raise TypeError("source_authority must be SourceAuthority")
        if not isinstance(self.source_format, SourceFormat):
            raise TypeError("source_format must be SourceFormat")
        if not isinstance(self.status, RawPolicyStatus):
            raise TypeError("status must be RawPolicyStatus")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
        for field_name in ("collection_id", "raw_policy_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not _IDENTIFIER_PATTERN.fullmatch(value):
                raise ValueError(f"{field_name} must be 3-64 lowercase identifier characters")
        for field_name in ("publisher", "collector", "media_type"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty")
        if not isinstance(self.content_sha256, str) or not _SHA256_PATTERN.fullmatch(
            self.content_sha256
        ):
            raise ValueError("content_sha256 must be a lowercase SHA-256 hex digest")
        _validate_source_url(self.source_url)
        _require_utc(self.collected_at, "collected_at")
        if self.status_updated_at is not None:
            _require_utc(self.status_updated_at, "status_updated_at")
            if self.status_updated_at < self.collected_at:
                raise ValueError("status_updated_at must not precede collected_at")
        elif self.status is not RawPolicyStatus.COLLECTED:
            raise ValueError("status_updated_at is required when status is not COLLECTED")
        if self.original_filename is not None:
            if not isinstance(self.original_filename, str):
                raise TypeError("original_filename must be a string or None")
            if PurePosixPath(self.original_filename).name != self.original_filename:
                raise ValueError("original_filename must be a basename")

    def to_dict(self) -> dict[str, str | None]:
        result = asdict(self)
        result["source_authority"] = self.source_authority.value
        result["source_format"] = self.source_format.value
        result["status"] = self.status.value
        result["collected_at"] = self.collected_at.isoformat().replace("+00:00", "Z")
        if self.status_updated_at is not None:
            result["status_updated_at"] = self.status_updated_at.isoformat().replace("+00:00", "Z")
        return result


def raw_storage_paths(
    metadata: RawPolicyMetadata, source_slug: str, extension: str
) -> tuple[PurePosixPath, PurePosixPath]:
    """Return raw object and JSON sidecar paths relative to POLICY_RAW_DATA_DIR."""

    if not _SLUG_PATTERN.fullmatch(source_slug):
        raise ValueError("source_slug must be a 3-64 character lowercase kebab-case slug")
    normalized_extension = extension.lower().removeprefix(".")
    if not re.fullmatch(r"[a-z0-9]{1,8}", normalized_extension):
        raise ValueError("extension must contain 1-8 lowercase alphanumeric characters")

    collected_date = metadata.collected_at.date()
    directory = PurePosixPath(
        f"{collected_date:%Y/%m/%d}",
        metadata.source_authority.value.lower(),
        source_slug,
    )
    basename = (
        f"{metadata.raw_policy_id}__{metadata.content_sha256}__{metadata.collection_id}"
    )
    return directory / f"{basename}.{normalized_extension}", directory / f"{basename}.metadata.json"
