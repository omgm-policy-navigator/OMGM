from __future__ import annotations

import csv
import hashlib
import json
import shutil
from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any

from app.modules.policies.csv_seed import load_policy_seed


class ChangeDetectionError(ValueError):
    pass


class ChangeStatus(StrEnum):
    UNCHANGED = "UNCHANGED"
    OUTDATED = "OUTDATED"
    REVIEWING = "REVIEWING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class SourceSnapshot:
    source_url: str
    media_type: str
    content: bytes
    collected_at: datetime
    extracted_fields: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.source_url.startswith(("http://", "https://")):
            raise ChangeDetectionError("source_url must be HTTP(S)")
        if not self.content:
            raise ChangeDetectionError("source content must not be empty")
        if self.collected_at.tzinfo is None:
            raise ChangeDetectionError("collected_at must be timezone-aware")
        object.__setattr__(self, "extracted_fields", MappingProxyType(dict(self.extracted_fields)))

    @property
    def content_sha256(self) -> str:
        return hashlib.sha256(self.content).hexdigest()


@dataclass(frozen=True)
class PolicyBaseline:
    policy_id: str
    source_url: str
    content_sha256: str
    fields: Mapping[str, Any]
    rule_dependencies: Mapping[str, frozenset[str]]
    document_chunks: Mapping[str, str]

    def __post_init__(self) -> None:
        invalid_hash = len(self.content_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.content_sha256
        )
        if invalid_hash:
            raise ChangeDetectionError("baseline content_sha256 must be a full SHA-256")
        object.__setattr__(self, "fields", MappingProxyType(dict(self.fields)))
        object.__setattr__(self, "rule_dependencies", MappingProxyType(dict(self.rule_dependencies)))
        object.__setattr__(self, "document_chunks", MappingProxyType(dict(self.document_chunks)))


@dataclass(frozen=True)
class FieldDiff:
    field: str
    before: Any
    after: Any


@dataclass(frozen=True)
class ReviewReport:
    report_id: str
    policy_id: str
    source_url: str
    baseline_sha256: str
    candidate_sha256: str
    status: ChangeStatus
    detected_at: datetime
    field_diffs: tuple[FieldDiff, ...]
    affected_rule_ids: tuple[str, ...]
    affected_chunk_ids: tuple[str, ...]
    required_actions: tuple[str, ...]
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None


@dataclass(frozen=True)
class SeedPatch:
    filename: str
    row_id: str
    values: Mapping[str, str]


def build_review_report(baseline: PolicyBaseline, candidate: SourceSnapshot) -> ReviewReport:
    if candidate.source_url != baseline.source_url:
        raise ChangeDetectionError("candidate source_url does not match the baseline")
    diffs = tuple(
        FieldDiff(field=field, before=baseline.fields.get(field), after=candidate.extracted_fields.get(field))
        for field in sorted(set(baseline.fields) | set(candidate.extracted_fields))
        if baseline.fields.get(field) != candidate.extracted_fields.get(field)
    )
    content_changed = baseline.content_sha256 != candidate.content_sha256
    changed = content_changed or bool(diffs)
    changed_fields = {item.field for item in diffs}
    affected_rules = tuple(
        sorted(rule_id for rule_id, dependencies in baseline.rule_dependencies.items() if dependencies & changed_fields)
    )
    affected_chunks = tuple(sorted(baseline.document_chunks)) if content_changed else ()
    status = ChangeStatus.OUTDATED if changed else ChangeStatus.UNCHANGED
    actions: list[str] = []
    if changed:
        actions.extend(("ADMIN_REVIEW", "SEED_REGENERATION"))
        if affected_rules:
            actions.append("REEVALUATE_AFFECTED_SESSIONS")
        if affected_chunks:
            actions.append("REINDEX_AFFECTED_CHUNKS")
    report_key = f"{baseline.policy_id}|{baseline.content_sha256}|{candidate.content_sha256}"
    return ReviewReport(
        report_id=f"change_{hashlib.sha256(report_key.encode()).hexdigest()[:20]}",
        policy_id=baseline.policy_id,
        source_url=baseline.source_url,
        baseline_sha256=baseline.content_sha256,
        candidate_sha256=candidate.content_sha256,
        status=status,
        detected_at=candidate.collected_at.astimezone(UTC),
        field_diffs=diffs,
        affected_rule_ids=affected_rules,
        affected_chunk_ids=affected_chunks,
        required_actions=tuple(actions),
    )


def approve_report(report: ReviewReport, reviewer: str, reviewed_at: datetime | None = None) -> ReviewReport:
    if report.status is not ChangeStatus.REVIEWING:
        raise ChangeDetectionError("only a reviewing candidate can be approved")
    reviewer = reviewer.strip()
    if not reviewer:
        raise ChangeDetectionError("reviewer must not be blank")
    return replace(
        report,
        status=ChangeStatus.APPROVED,
        reviewed_by=reviewer,
        reviewed_at=(reviewed_at or datetime.now(UTC)).astimezone(UTC),
    )


def begin_review(report: ReviewReport) -> ReviewReport:
    if report.status is not ChangeStatus.OUTDATED:
        raise ChangeDetectionError("only an outdated candidate can enter review")
    return replace(report, status=ChangeStatus.REVIEWING)


def write_review_report(report: ReviewReport, destination: Path) -> None:
    if destination.exists():
        raise ChangeDetectionError("review history reports are append-only")
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(report)
    payload["status"] = report.status.value
    payload["detected_at"] = report.detected_at.isoformat()
    payload["reviewed_at"] = report.reviewed_at.isoformat() if report.reviewed_at else None
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    temporary.replace(destination)


def regenerate_seed(
    report: ReviewReport,
    baseline_seed_dir: Path,
    output_dir: Path,
    patches: tuple[SeedPatch, ...] = (),
) -> Path:
    if report.status is not ChangeStatus.APPROVED:
        raise ChangeDetectionError("seed regeneration requires an approved review report")
    source = baseline_seed_dir.resolve()
    target = output_dir.resolve()
    if source == target or source in target.parents:
        raise ChangeDetectionError("output_dir must be outside the active Seed directory")
    if target.exists():
        raise ChangeDetectionError("output_dir must not already exist")
    shutil.copytree(source, target)
    try:
        for patch in patches:
            _apply_patch(target, patch)
        _write_checksums(target)
        load_policy_seed(target)
    except Exception:
        shutil.rmtree(target)
        raise
    return target


def _apply_patch(directory: Path, patch: SeedPatch) -> None:
    if Path(patch.filename).name != patch.filename or patch.filename == "SHA256SUMS":
        raise ChangeDetectionError("patch filename is not allowed")
    path = directory / patch.filename
    if not path.is_file() or path.suffix.lower() != ".csv":
        raise ChangeDetectionError(f"patch target is not a Seed CSV: {patch.filename}")
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    unknown = set(patch.values) - set(fieldnames)
    if unknown or "id" not in fieldnames:
        raise ChangeDetectionError("patch contains an unknown field or target has no id")
    matches = [row for row in rows if row["id"] == patch.row_id]
    if len(matches) != 1:
        raise ChangeDetectionError("patch row_id must match exactly one row")
    matches[0].update(patch.values)
    with path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)


def _write_checksums(directory: Path) -> None:
    files = sorted(path for path in directory.iterdir() if path.is_file() and path.name != "SHA256SUMS")
    lines = []
    for path in files:
        normalized = path.read_bytes().replace(b"\r\n", b"\n")
        lines.append(f"{hashlib.sha256(normalized).hexdigest()}  {path.name}")
    (directory / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
