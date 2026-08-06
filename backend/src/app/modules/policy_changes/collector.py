from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

import httpx

from app.modules.policy_changes.workflow import ChangeDetectionError, SourceSnapshot

ALLOWED_MEDIA_TYPES = {"application/json", "text/html", "application/pdf"}


class OfficialSourceCollector:
    def __init__(self, client: httpx.AsyncClient, *, max_bytes: int = 5_000_000) -> None:
        self.client = client
        self.max_bytes = max_bytes

    async def collect(
        self,
        source_url: str,
        *,
        expected_host: str,
        field_mapping: Mapping[str, str] | None = None,
        extractor: Callable[[bytes, str], Mapping[str, Any]] | None = None,
    ) -> SourceSnapshot:
        parsed = httpx.URL(source_url)
        if parsed.scheme not in {"http", "https"} or parsed.host != expected_host:
            raise ChangeDetectionError("source URL is not on the configured official host")
        async with self.client.stream("GET", source_url, follow_redirects=False) as response:
            response.raise_for_status()
            if response.url.host != expected_host:
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
        if extractor is not None:
            fields = dict(extractor(content, media_type))
        elif media_type == "application/json":
            payload = json.loads(content)
            if not isinstance(payload, dict):
                raise ChangeDetectionError("source API response must be an object")
            fields = _extract_fields(payload, field_mapping or {})
        return SourceSnapshot(
            source_url=source_url,
            media_type=media_type,
            content=content,
            collected_at=datetime.now(UTC),
            extracted_fields=fields,
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
