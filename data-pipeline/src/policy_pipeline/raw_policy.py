"""Raw policy source contract and deterministic storage naming rules."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import PurePosixPath
from urllib.parse import parse_qsl, urlsplit


SCHEMA_VERSION = "1.0"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")
_SENSITIVE_QUERY_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "authorization",
    "key",
    "password",
    "secret",
    "service_key",
    "servicekey",
    "token",
}


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
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError(f"{field_name} must be timezone-aware UTC")


def _validate_source_url(value: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("source_url must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password:
        raise ValueError("source_url must not contain credentials")
    query_keys = {key.lower() for key, _ in parse_qsl(parsed.query, keep_blank_values=True)}
    if query_keys & _SENSITIVE_QUERY_KEYS:
        raise ValueError("source_url must not contain secret query parameters")


@dataclass(frozen=True, slots=True)
class RawPolicyMetadata:
    """Sidecar metadata for one immutable raw policy source object."""

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
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
        if not _IDENTIFIER_PATTERN.fullmatch(self.raw_policy_id):
            raise ValueError("raw_policy_id must be 3-64 lowercase identifier characters")
        if not self.publisher.strip():
            raise ValueError("publisher must not be empty")
        if not self.collector.strip():
            raise ValueError("collector must not be empty")
        if not self.media_type.strip():
            raise ValueError("media_type must not be empty")
        if not _SHA256_PATTERN.fullmatch(self.content_sha256):
            raise ValueError("content_sha256 must be a lowercase SHA-256 hex digest")
        _validate_source_url(self.source_url)
        _require_utc(self.collected_at, "collected_at")
        if self.status_updated_at is not None:
            _require_utc(self.status_updated_at, "status_updated_at")
            if self.status_updated_at < self.collected_at:
                raise ValueError("status_updated_at must not precede collected_at")
        if self.original_filename is not None:
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
    basename = f"{metadata.raw_policy_id}__{metadata.content_sha256[:12]}"
    return directory / f"{basename}.{normalized_extension}", directory / f"{basename}.metadata.json"
