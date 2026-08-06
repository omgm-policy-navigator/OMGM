from __future__ import annotations

import csv
import hashlib
import json
import shutil
from collections.abc import Mapping
from dataclasses import dataclass, replace
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


class ExtractionStatus(StrEnum):
    EXTRACTED = "EXTRACTED"
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    FAILED = "FAILED"


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    return value


@dataclass(frozen=True)
class SourceSnapshot:
    source_url: str
    media_type: str
    content: bytes
    collected_at: datetime
    extracted_fields: Mapping[str, Any]
    extraction_status: ExtractionStatus = ExtractionStatus.EXTRACTED
    extractor_name: str = "manual"
    extractor_version: str = "1"
    field_mapping_version: str = "1"

    def __post_init__(self) -> None:
        if not self.source_url.startswith(("http://", "https://")):
            raise ChangeDetectionError("source_url must be HTTP(S)")
        if not self.content:
            raise ChangeDetectionError("source content must not be empty")
        if self.collected_at.tzinfo is None:
            raise ChangeDetectionError("collected_at must be timezone-aware")
        for value in (self.extractor_name, self.extractor_version, self.field_mapping_version):
            if not value.strip():
                raise ChangeDetectionError("extractor identity fields must not be blank")
        if self.extraction_status is not ExtractionStatus.EXTRACTED and self.extracted_fields:
            raise ChangeDetectionError("unextracted snapshots must not contain extracted fields")
        object.__setattr__(self, "extracted_fields", _freeze(self.extracted_fields))

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
        object.__setattr__(self, "fields", _freeze(self.fields))
        object.__setattr__(self, "rule_dependencies", _freeze(self.rule_dependencies))
        object.__setattr__(self, "document_chunks", _freeze(self.document_chunks))


@dataclass(frozen=True)
class FieldDiff:
    field: str
    before: Any
    after: Any


@dataclass(frozen=True)
class SeedPatch:
    filename: str
    row_id: str
    values: Mapping[str, str]

    def __post_init__(self) -> None:
        if not self.row_id.strip() or not self.values:
            raise ChangeDetectionError("Seed patch requires a row and at least one value")
        if any(not isinstance(key, str) or not isinstance(value, str) for key, value in self.values.items()):
            raise ChangeDetectionError("Seed patch keys and values must be strings")
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))


@dataclass(frozen=True)
class ReviewReport:
    report_id: str
    policy_id: str
    source_url: str
    baseline_sha256: str
    candidate_sha256: str
    extractor_name: str
    extractor_version: str
    field_mapping_version: str
    extraction_status: ExtractionStatus
    status: ChangeStatus
    detected_at: datetime
    field_diffs: tuple[FieldDiff, ...]
    affected_rule_ids: tuple[str, ...]
    affected_chunk_ids: tuple[str, ...]
    required_actions: tuple[str, ...]
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    approved_patches: tuple[SeedPatch, ...] = ()


@dataclass(frozen=True)
class RegenerationManifest:
    report_id: str
    baseline_seed_hash: str
    generated_seed_hash: str
    applied_patch_count: int
    applied_rows: tuple[str, ...]


def build_review_report(baseline: PolicyBaseline, candidate: SourceSnapshot) -> ReviewReport:
    if candidate.source_url != baseline.source_url:
        raise ChangeDetectionError("candidate source_url does not match the baseline")
    diffs: tuple[FieldDiff, ...] = ()
    if candidate.extraction_status is ExtractionStatus.EXTRACTED:
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
    actions: list[str] = []
    if changed:
        actions.extend(("ADMIN_REVIEW", "SEED_REGENERATION"))
        if affected_rules:
            actions.append("REEVALUATE_AFFECTED_SESSIONS")
        if affected_chunks:
            actions.append("REINDEX_AFFECTED_CHUNKS")
    diff_payload = json.dumps(
        [{"field": item.field, "before": _jsonable(item.before), "after": _jsonable(item.after)} for item in diffs],
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    report_key = "|".join(
        (
            baseline.policy_id,
            baseline.content_sha256,
            candidate.content_sha256,
            candidate.extractor_name,
            candidate.extractor_version,
            candidate.field_mapping_version,
            candidate.extraction_status.value,
            hashlib.sha256(diff_payload.encode()).hexdigest(),
        )
    )
    return ReviewReport(
        report_id=f"change_{hashlib.sha256(report_key.encode()).hexdigest()[:20]}",
        policy_id=baseline.policy_id,
        source_url=baseline.source_url,
        baseline_sha256=baseline.content_sha256,
        candidate_sha256=candidate.content_sha256,
        extractor_name=candidate.extractor_name,
        extractor_version=candidate.extractor_version,
        field_mapping_version=candidate.field_mapping_version,
        extraction_status=candidate.extraction_status,
        status=ChangeStatus.OUTDATED if changed else ChangeStatus.UNCHANGED,
        detected_at=candidate.collected_at.astimezone(UTC),
        field_diffs=diffs,
        affected_rule_ids=affected_rules,
        affected_chunk_ids=affected_chunks,
        required_actions=tuple(actions),
    )


def begin_review(report: ReviewReport) -> ReviewReport:
    if report.status is not ChangeStatus.OUTDATED:
        raise ChangeDetectionError("only an outdated candidate can enter review")
    return replace(report, status=ChangeStatus.REVIEWING)


def approve_report(
    report: ReviewReport,
    reviewer: str,
    *,
    approved_patches: tuple[SeedPatch, ...],
    reviewed_at: datetime | None = None,
) -> ReviewReport:
    if report.status is not ChangeStatus.REVIEWING:
        raise ChangeDetectionError("only a reviewing candidate can be approved")
    reviewer = reviewer.strip()
    if not reviewer:
        raise ChangeDetectionError("reviewer must not be blank")
    if reviewed_at is not None and reviewed_at.tzinfo is None:
        raise ChangeDetectionError("reviewed_at must be timezone-aware")
    _validate_patches_against_report(report, approved_patches)
    return replace(
        report,
        status=ChangeStatus.APPROVED,
        reviewed_by=reviewer,
        reviewed_at=(reviewed_at or datetime.now(UTC)).astimezone(UTC),
        approved_patches=tuple(approved_patches),
    )


def _validate_patches_against_report(report: ReviewReport, patches: tuple[SeedPatch, ...]) -> None:
    if report.baseline_sha256 != report.candidate_sha256 and not patches:
        raise ChangeDetectionError("changed source requires at least one approved patch")
    changed_fields = {item.field: item.after for item in report.field_diffs}
    covered_fields: set[str] = set()
    has_derived_patch = False
    seen: set[tuple[str, str]] = set()
    for patch in patches:
        identity = (patch.filename, patch.row_id)
        if identity in seen:
            raise ChangeDetectionError("duplicate Seed patch target")
        seen.add(identity)
        if patch.filename in {"02_policy.csv", "08_policy_document.csv", "09_policy_flat.csv"}:
            if patch.row_id != report.policy_id:
                raise ChangeDetectionError("patch targets another policy")
        elif patch.filename == "03_policy_rule.csv":
            if patch.row_id not in report.affected_rule_ids:
                raise ChangeDetectionError("patch targets an unaffected rule")
            has_derived_patch = True
        elif patch.filename == "10_policy_document_chunk.csv":
            if patch.row_id not in report.affected_chunk_ids:
                raise ChangeDetectionError("patch targets an unaffected chunk")
            has_derived_patch = True
        else:
            raise ChangeDetectionError("patch target is outside the approved D6 scope")
        if patch.filename == "02_policy.csv":
            for field, value in patch.values.items():
                if field == "verified_at":
                    continue
                if field not in changed_fields or _seed_text(changed_fields[field]) != value:
                    raise ChangeDetectionError("policy patch value was not approved by the field diff")
                covered_fields.add(field)
        elif patch.filename in {"08_policy_document.csv", "09_policy_flat.csv"}:
            has_derived_patch = True
    if set(changed_fields) - covered_fields and not has_derived_patch:
        raise ChangeDetectionError("approved patches do not cover the reviewed field changes")


def _seed_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def write_review_report(report: ReviewReport, destination: Path) -> None:
    if destination.exists():
        raise ChangeDetectionError("review history reports are append-only")
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "report_id": report.report_id,
        "policy_id": report.policy_id,
        "source_url": report.source_url,
        "baseline_sha256": report.baseline_sha256,
        "candidate_sha256": report.candidate_sha256,
        "extractor_name": report.extractor_name,
        "extractor_version": report.extractor_version,
        "field_mapping_version": report.field_mapping_version,
        "extraction_status": report.extraction_status.value,
        "status": report.status.value,
        "detected_at": report.detected_at.isoformat(),
        "field_diffs": [
            {"field": item.field, "before": _jsonable(item.before), "after": _jsonable(item.after)}
            for item in report.field_diffs
        ],
        "affected_rule_ids": list(report.affected_rule_ids),
        "affected_chunk_ids": list(report.affected_chunk_ids),
        "required_actions": list(report.required_actions),
        "reviewed_by": report.reviewed_by,
        "reviewed_at": report.reviewed_at.isoformat() if report.reviewed_at else None,
        "approved_patches": [
            {"filename": patch.filename, "row_id": patch.row_id, "values": dict(patch.values)}
            for patch in report.approved_patches
        ],
    }
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    temporary.replace(destination)


def regenerate_seed(report: ReviewReport, baseline_seed_dir: Path, output_dir: Path) -> Path:
    if report.status is not ChangeStatus.APPROVED:
        raise ChangeDetectionError("seed regeneration requires an approved review report")
    if report.baseline_sha256 != report.candidate_sha256 and not report.approved_patches:
        raise ChangeDetectionError("changed source requires at least one approved patch")
    source = baseline_seed_dir.resolve()
    target = output_dir.resolve()
    if source == target or source in target.parents:
        raise ChangeDetectionError("output_dir must be outside the active Seed directory")
    if target.exists():
        raise ChangeDetectionError("output_dir must not already exist")
    baseline_seed_hash = _directory_hash(source)
    shutil.copytree(source, target)
    try:
        for patch in report.approved_patches:
            _apply_patch(target, patch, report.policy_id)
        generated_seed_hash = _directory_hash(target)
        manifest = RegenerationManifest(
            report_id=report.report_id,
            baseline_seed_hash=baseline_seed_hash,
            generated_seed_hash=generated_seed_hash,
            applied_patch_count=len(report.approved_patches),
            applied_rows=tuple(f"{patch.filename}:{patch.row_id}" for patch in report.approved_patches),
        )
        (target / "D6_REGENERATION_MANIFEST.json").write_text(
            json.dumps(
                {
                    "reportId": manifest.report_id,
                    "baselineSeedHash": manifest.baseline_seed_hash,
                    "generatedSeedHash": manifest.generated_seed_hash,
                    "appliedPatchCount": manifest.applied_patch_count,
                    "appliedRows": list(manifest.applied_rows),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        _write_checksums(target)
        load_policy_seed(target)
    except Exception:
        shutil.rmtree(target)
        raise
    return target


def _apply_patch(directory: Path, patch: SeedPatch, policy_id: str) -> None:
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
    if patch.filename in {"03_policy_rule.csv", "08_policy_document.csv", "10_policy_document_chunk.csv"}:
        if matches[0].get("policy_id") != policy_id:
            raise ChangeDetectionError("patch row belongs to another policy")
    matches[0].update(patch.values)
    with path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)


def _directory_hash(directory: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in directory.iterdir() if item.is_file() and item.name != "SHA256SUMS"):
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
        digest.update(b"\0")
    return digest.hexdigest()


def _write_checksums(directory: Path) -> None:
    files = sorted(path for path in directory.iterdir() if path.is_file() and path.name != "SHA256SUMS")
    lines = []
    for path in files:
        normalized = path.read_bytes().replace(b"\r\n", b"\n")
        lines.append(f"{hashlib.sha256(normalized).hexdigest()}  {path.name}")
    (directory / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
