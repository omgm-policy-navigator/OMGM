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
    )


def baseline(source: SourceSnapshot) -> PolicyBaseline:
    return PolicyBaseline(
        policy_id="policy-1",
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
    before = snapshot(b"old", {"income_limit": 50, "title": "Policy"})
    report = approve_report(
        begin_review(build_review_report(baseline(before), snapshot(b"new", {"income_limit": 60, "title": "Policy"}))),
        reviewer="policy-admin",
        reviewed_at=datetime(2026, 8, 7, tzinfo=UTC),
    )
    output = tmp_path / "candidate-seed"

    regenerated = regenerate_seed(
        report,
        SEED_DIR,
        output,
        patches=(SeedPatch(filename="02_policy.csv", row_id="1", values={"verified_at": "2026-08-07"}),),
    )

    assert regenerated == output.resolve()
    assert report.status is ChangeStatus.APPROVED
    assert load_policy_seed(output).policies["1"].verified_at.isoformat() == "2026-08-07"
    assert SEED_DIR.joinpath("02_policy.csv").read_text(encoding="utf-8").splitlines()[1].endswith("2026-08-05")


def test_approval_cannot_skip_reviewing_state() -> None:
    before = snapshot(b"old", {"income_limit": 50, "title": "Policy"})
    report = build_review_report(baseline(before), snapshot(b"new", {"income_limit": 60, "title": "Policy"}))

    with pytest.raises(ChangeDetectionError, match="reviewing"):
        approve_report(report, reviewer="policy-admin")


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
            collector = OfficialSourceCollector(client)
            return await collector.collect(
                "https://official.example/api/policy/1",
                expected_host="official.example",
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
            collector = OfficialSourceCollector(client)
            with pytest.raises(ChangeDetectionError, match="official host"):
                await collector.collect("https://evil.example/policy", expected_host="official.example")
            with pytest.raises(ChangeDetectionError, match="media type"):
                await collector.collect("https://official.example/policy", expected_host="official.example")

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
            return await OfficialSourceCollector(client).collect(
                "https://official.example/policy",
                expected_host="official.example",
                extractor=lambda content, media_type: {
                    "title": "Updated Policy" if b"Updated Policy" in content else None,
                    "media_type": media_type,
                },
            )

    result = asyncio.run(run())

    assert result.extracted_fields == {"title": "Updated Policy", "media_type": "text/html"}
