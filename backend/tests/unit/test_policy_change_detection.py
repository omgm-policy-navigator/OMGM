import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from app.modules.policies.csv_seed import load_policy_seed
from app.modules.policy_changes.collector import OfficialSourceCollector
from app.modules.policy_changes.workflow import (
    ChangeDetectionError,
    ChangeStatus,
    ExtractionStatus,
    PolicyBaseline,
    SeedPatch,
    SourceSnapshot,
    approve_report,
    begin_review,
    build_review_report,
    regenerate_seed,
    write_review_report,
)

SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "policy-seed"


def snapshot(content: bytes, fields: dict | None = None, media_type: str = "text/html") -> SourceSnapshot:
    return SourceSnapshot(
        source_url="https://official.example/policy/1",
        media_type=media_type,
        content=content,
        collected_at=datetime(2026, 8, 6, tzinfo=UTC),
        extracted_fields=fields or {},
        extractor_name="test-extractor",
        extractor_version="1",
        field_mapping_version="1",
    )


def baseline(source: SourceSnapshot) -> PolicyBaseline:
    return PolicyBaseline(
        policy_id="1",
        source_url=source.source_url,
        content_sha256=source.content_sha256,
        fields={"income_limit": 50, "title": "Policy"},
        rule_dependencies={
            "rule-income": frozenset({"income_limit"}),
            "rule-region": frozenset({"region"}),
        },
        document_chunks={"chunk-1": "hash-1", "chunk-2": "hash-2"},
    )


def test_unchanged_html_does_not_create_review_work() -> None:
    current = snapshot(b"<html>same</html>", {"income_limit": 50, "title": "Policy"})

    report = build_review_report(baseline(current), current)

    assert report.status is ChangeStatus.UNCHANGED
    assert report.field_diffs == ()
    assert report.affected_rule_ids == ()
    assert report.affected_chunk_ids == ()
    assert report.required_actions == ()


@pytest.mark.parametrize("media_type,content", [("text/html", b"<html>new</html>"), ("application/pdf", b"%PDF-new")])
def test_html_and_pdf_hash_change_become_outdated(media_type: str, content: bytes) -> None:
    before = snapshot(b"old", {"income_limit": 50, "title": "Policy"}, media_type)
    after = snapshot(content, {"income_limit": 60, "title": "Policy"}, media_type)

    report = build_review_report(baseline(before), after)

    assert report.status is ChangeStatus.OUTDATED
    assert [(item.field, item.before, item.after) for item in report.field_diffs] == [("income_limit", 50, 60)]
    assert report.affected_rule_ids == ("rule-income",)
    assert report.affected_chunk_ids == ("chunk-1", "chunk-2")
    assert "REEVALUATE_AFFECTED_SESSIONS" in report.required_actions
    assert "REINDEX_AFFECTED_CHUNKS" in report.required_actions


def test_missing_candidate_field_is_explicit_diff_not_false_or_zero() -> None:
    before = snapshot(b"old", {"income_limit": 50, "title": "Policy"})
    after = snapshot(b"new", {"title": "Policy"})

    report = build_review_report(baseline(before), after)

    assert report.field_diffs[0].field == "income_limit"
    assert report.field_diffs[0].after is None


def test_review_report_history_is_written_without_raw_source(tmp_path: Path) -> None:
    before = snapshot(b"old", {"income_limit": 50, "title": "Policy"})
    report = build_review_report(baseline(before), snapshot(b"new", {"income_limit": 60, "title": "Policy"}))
    destination = tmp_path / "reports" / f"{report.report_id}.json"

    write_review_report(report, destination)
    payload = json.loads(destination.read_text(encoding="utf-8"))

    assert payload["status"] == "OUTDATED"
    assert payload["affected_rule_ids"] == ["rule-income"]
    assert "old" not in destination.read_text(encoding="utf-8")
    assert "new" not in destination.read_text(encoding="utf-8")
    with pytest.raises(ChangeDetectionError, match="append-only"):
        write_review_report(report, destination)


def test_seed_regeneration_is_blocked_before_approval(tmp_path: Path) -> None:
    before = snapshot(b"old", {"income_limit": 50, "title": "Policy"})
    report = build_review_report(baseline(before), snapshot(b"new", {"income_limit": 60, "title": "Policy"}))

    with pytest.raises(ChangeDetectionError, match="approved"):
        regenerate_seed(report, SEED_DIR, tmp_path / "candidate-seed")

    assert not (tmp_path / "candidate-seed").exists()


def test_approved_report_regenerates_valid_staged_seed(tmp_path: Path) -> None:
    before = snapshot(b"old", {"summary": "Old summary"})
    seed_baseline = PolicyBaseline(
        policy_id="1",
        source_url=before.source_url,
        content_sha256=before.content_sha256,
        fields={"summary": "Old summary"},
        rule_dependencies={},
        document_chunks={},
    )
    patch = SeedPatch(filename="02_policy.csv", row_id="1", values={"summary": "Updated summary"})
    report = approve_report(
        begin_review(build_review_report(seed_baseline, snapshot(b"new", {"summary": "Updated summary"}))),
        reviewer="policy-admin",
        approved_patches=(patch,),
        reviewed_at=datetime(2026, 8, 7, tzinfo=UTC),
    )
    output = tmp_path / "candidate-seed"

    regenerated = regenerate_seed(report, SEED_DIR, output)

    assert regenerated == output.resolve()
    assert report.status is ChangeStatus.APPROVED
    assert load_policy_seed(output).policies["1"].summary == "Updated summary"
    manifest = json.loads((output / "D6_REGENERATION_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["reportId"] == report.report_id
    assert manifest["appliedPatchCount"] == 1
    report_path = tmp_path / "approved-report.json"
    write_review_report(report, report_path)
    assert json.loads(report_path.read_text(encoding="utf-8"))["approved_patches"][0]["row_id"] == "1"
    assert SEED_DIR.joinpath("02_policy.csv").read_text(encoding="utf-8").splitlines()[1].endswith("2026-08-05")


def test_approval_cannot_skip_reviewing_state() -> None:
    before = snapshot(b"old", {"income_limit": 50, "title": "Policy"})
    report = build_review_report(baseline(before), snapshot(b"new", {"income_limit": 60, "title": "Policy"}))

    with pytest.raises(ChangeDetectionError, match="reviewing"):
        approve_report(report, reviewer="policy-admin", approved_patches=())


def test_api_collector_maps_fields_and_keeps_credentials_out_of_snapshot() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "official.example"
        return httpx.Response(
            200,
            json={"policy": {"title": "Updated", "income": 60}},
            headers={"content-type": "application/json"},
            request=request,
        )

    async def run() -> SourceSnapshot:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            collector = OfficialSourceCollector(client, allowed_hosts={"official.example"})
            return await collector.collect(
                "https://official.example/api/policy/1",
                field_mapping={"title": "policy.title", "income_limit": "policy.income"},
            )

    result = asyncio.run(run())

    assert result.extracted_fields == {"title": "Updated", "income_limit": 60}
    assert not hasattr(result, "headers")


def test_collector_rejects_untrusted_host_and_unsupported_media_type() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"image", headers={"content-type": "image/png"}, request=request)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            collector = OfficialSourceCollector(client, allowed_hosts={"official.example"})
            with pytest.raises(ChangeDetectionError, match="official host"):
                await collector.collect("https://evil.example/policy")
            with pytest.raises(ChangeDetectionError, match="media type"):
                await collector.collect("https://official.example/policy")

    asyncio.run(run())


def test_html_collector_uses_explicit_field_extractor() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"<h1>Updated Policy</h1>",
            headers={"content-type": "text/html; charset=utf-8"},
            request=request,
        )

    async def run() -> SourceSnapshot:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await OfficialSourceCollector(client, allowed_hosts={"official.example"}).collect(
                "https://official.example/policy",
                extractor=lambda content, media_type: {
                    "title": "Updated Policy" if b"Updated Policy" in content else None,
                    "media_type": media_type,
                },
            )

    result = asyncio.run(run())

    assert result.extracted_fields == {"title": "Updated Policy", "media_type": "text/html"}


def test_html_and_pdf_require_extractor() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"<html>changed</html>",
            headers={"content-type": "text/html"},
            request=request,
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            collector = OfficialSourceCollector(client, allowed_hosts={"official.example"})
            with pytest.raises(ChangeDetectionError, match="requires an extractor"):
                await collector.collect("https://official.example/policy")

    asyncio.run(run())


def test_not_attempted_extraction_does_not_create_field_deletions() -> None:
    before = snapshot(b"old", {"income_limit": 50, "title": "Policy"})
    candidate = SourceSnapshot(
        source_url=before.source_url,
        media_type="text/html",
        content=b"new",
        collected_at=datetime(2026, 8, 6, tzinfo=UTC),
        extracted_fields={},
        extraction_status=ExtractionStatus.NOT_ATTEMPTED,
        extractor_name="none",
        extractor_version="1",
        field_mapping_version="1",
    )

    report = build_review_report(baseline(before), candidate)

    assert report.status is ChangeStatus.OUTDATED
    assert report.field_diffs == ()
    assert report.affected_rule_ids == ()


def test_extractor_version_and_fields_change_report_identity() -> None:
    before = snapshot(b"same", {"income_limit": 50, "title": "Policy"})
    first = snapshot(b"same", {"income_limit": 60, "title": "Policy"})
    second = SourceSnapshot(
        source_url=before.source_url,
        media_type="text/html",
        content=b"same",
        collected_at=datetime(2026, 8, 6, tzinfo=UTC),
        extracted_fields={"income_limit": 70, "title": "Policy"},
        extractor_name="test-extractor",
        extractor_version="2",
        field_mapping_version="1",
    )

    first_report = build_review_report(baseline(before), first)
    second_report = build_review_report(baseline(before), second)
    assert first_report.report_id != second_report.report_id


def test_seed_patch_values_are_frozen_at_approval() -> None:
    values = {"summary": "Approved"}
    patch = SeedPatch(filename="02_policy.csv", row_id="1", values=values)
    values["summary"] = "Mutated"

    assert patch.values["summary"] == "Approved"


def test_changed_report_cannot_be_approved_without_patch() -> None:
    before = snapshot(b"old", {"income_limit": 50, "title": "Policy"})
    report = begin_review(build_review_report(baseline(before), snapshot(b"new", {"income_limit": 60})))

    with pytest.raises(ChangeDetectionError, match="at least one approved patch"):
        approve_report(report, reviewer="policy-admin", approved_patches=())


def test_approved_report_cannot_patch_another_policy() -> None:
    before = snapshot(b"old", {"summary": "Old"})
    report = begin_review(build_review_report(baseline(before), snapshot(b"new", {"summary": "New"})))
    patch = SeedPatch(filename="02_policy.csv", row_id="2", values={"summary": "New"})

    with pytest.raises(ChangeDetectionError, match="another policy"):
        approve_report(report, reviewer="policy-admin", approved_patches=(patch,))


@pytest.mark.parametrize(
    "patch",
    [
        SeedPatch(filename="03_policy_rule.csv", row_id="unaffected-rule", values={"expected_value": "60"}),
        SeedPatch(filename="10_policy_document_chunk.csv", row_id="unaffected-chunk", values={"content": "new"}),
    ],
)
def test_approved_report_cannot_patch_unaffected_rule_or_chunk(patch: SeedPatch) -> None:
    before = snapshot(b"old", {"income_limit": 50, "title": "Policy"})
    report = begin_review(build_review_report(baseline(before), snapshot(b"new", {"income_limit": 60})))

    with pytest.raises(ChangeDetectionError, match="unaffected"):
        approve_report(report, reviewer="policy-admin", approved_patches=(patch,))


def test_verified_date_only_does_not_complete_field_change() -> None:
    before = snapshot(b"old", {"summary": "Old"})
    report = begin_review(build_review_report(baseline(before), snapshot(b"new", {"summary": "New"})))
    patch = SeedPatch(filename="02_policy.csv", row_id="1", values={"verified_at": "2026-08-07"})

    with pytest.raises(ChangeDetectionError, match="do not cover"):
        approve_report(report, reviewer="policy-admin", approved_patches=(patch,))


def test_plain_http_is_rejected_by_default() -> None:
    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200))) as client:
            collector = OfficialSourceCollector(client, allowed_hosts={"official.example"})
            with pytest.raises(ChangeDetectionError, match="HTTPS"):
                await collector.collect("http://official.example/policy")

    asyncio.run(run())
