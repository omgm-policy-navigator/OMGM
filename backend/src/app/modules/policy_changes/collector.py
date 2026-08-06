from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

import httpx

from app.modules.policy_changes.workflow import ChangeDetectionError, ExtractionStatus, SourceSnapshot

ALLOWED_MEDIA_TYPES = {"application/json", "text/html", "application/pdf"}


class OfficialSourceCollector:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        allowed_hosts: set[str],
        max_bytes: int = 5_000_000,
        allow_insecure_http: bool = False,
    ) -> None:
        if not allowed_hosts:
            raise ChangeDetectionError("at least one official host must be configured")
        self.client = client
        self.allowed_hosts = frozenset(host.lower() for host in allowed_hosts)
        self.max_bytes = max_bytes
        self.allow_insecure_http = allow_insecure_http

    async def collect(
        self,
        source_url: str,
        *,
        field_mapping: Mapping[str, str] | None = None,
        extractor: Callable[[bytes, str], Mapping[str, Any]] | None = None,
        extractor_name: str = "official-source-extractor",
        extractor_version: str = "1",
        field_mapping_version: str = "1",
    ) -> SourceSnapshot:
        parsed = httpx.URL(source_url)
        allowed_scheme = parsed.scheme == "https" or (self.allow_insecure_http and parsed.scheme == "http")
        if not allowed_scheme:
            raise ChangeDetectionError("official source URL must use HTTPS")
        if parsed.host not in self.allowed_hosts:
            raise ChangeDetectionError("source URL is not on the configured official host")
        if parsed.userinfo:
            raise ChangeDetectionError("source URL must not contain credentials")
        async with self.client.stream("GET", source_url, follow_redirects=False) as response:
            response.raise_for_status()
            if response.url.host not in self.allowed_hosts:
                raise ChangeDetectionError("source response left the configured official host")
            media_type = response.headers.get("content-type", "").split(";", maxsplit=1)[0].strip().lower()
            if media_type not in ALLOWED_MEDIA_TYPES:
                raise ChangeDetectionError("source media type is not supported")
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > self.max_bytes:
                    raise ChangeDetectionError("source response size is invalid")
            content = bytes(body)
            if not content:
                raise ChangeDetectionError("source response size is invalid")
        fields: dict[str, Any] = {}
        extraction_status = ExtractionStatus.EXTRACTED
        if extractor is not None:
            fields = dict(extractor(content, media_type))
        elif media_type == "application/json":
            payload = json.loads(content)
            if not isinstance(payload, dict):
                raise ChangeDetectionError("source API response must be an object")
            fields = _extract_fields(payload, field_mapping or {})
            extractor_name = "json-field-mapping"
        else:
            raise ChangeDetectionError(f"{media_type} source requires an extractor")
        return SourceSnapshot(
            source_url=source_url,
            media_type=media_type,
            content=content,
            collected_at=datetime.now(UTC),
            extracted_fields=fields,
            extraction_status=extraction_status,
            extractor_name=extractor_name,
            extractor_version=extractor_version,
            field_mapping_version=field_mapping_version,
        )


def _extract_fields(payload: dict[str, Any], field_mapping: Mapping[str, str]) -> dict[str, Any]:
    extracted: dict[str, Any] = {}
    for target, source in field_mapping.items():
        value: Any = payload
        for part in source.split("."):
            if not isinstance(value, dict) or part not in value:
                value = None
                break
            value = value[part]
        extracted[target] = value
    return extracted
