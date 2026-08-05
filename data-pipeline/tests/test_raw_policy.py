import unittest
from datetime import datetime, timezone

from policy_pipeline.raw_policy import (
    RawPolicyMetadata,
    RawPolicyStatus,
    SourceAuthority,
    SourceFormat,
    raw_storage_paths,
    sha256_bytes,
)


class RawPolicyMetadataTests(unittest.TestCase):
    def build_metadata(self, **overrides: object) -> RawPolicyMetadata:
        values = {
            "raw_policy_id": "raw-policy-001",
            "source_authority": SourceAuthority.OFFICIAL,
            "source_format": SourceFormat.PDF,
            "source_url": "https://agency.example.go.kr/notices/123",
            "publisher": "샘플 정책기관",
            "collected_at": datetime(2026, 8, 5, 3, 4, 5, tzinfo=timezone.utc),
            "content_sha256": sha256_bytes(b"sample public policy document"),
            "media_type": "application/pdf",
            "original_filename": "notice.pdf",
        }
        values.update(overrides)
        return RawPolicyMetadata(**values)  # type: ignore[arg-type]

    def test_serializes_enums_and_utc_timestamps(self) -> None:
        result = self.build_metadata(status=RawPolicyStatus.REVIEWING).to_dict()

        self.assertEqual(result["source_authority"], "OFFICIAL")
        self.assertEqual(result["status"], "REVIEWING")
        self.assertEqual(result["collected_at"], "2026-08-05T03:04:05Z")

    def test_builds_deterministic_raw_and_sidecar_paths(self) -> None:
        metadata = self.build_metadata()

        content_path, metadata_path = raw_storage_paths(metadata, "sample-agency", ".PDF")

        prefix = "2026/08/05/official/sample-agency/raw-policy-001__"
        self.assertTrue(content_path.as_posix().startswith(prefix))
        self.assertTrue(content_path.as_posix().endswith(".pdf"))
        self.assertTrue(metadata_path.as_posix().endswith(".metadata.json"))

    def test_rejects_non_utc_collection_time(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone-aware UTC"):
            self.build_metadata(collected_at=datetime(2026, 8, 5, 3, 4, 5))

    def test_rejects_secret_in_source_url(self) -> None:
        with self.assertRaisesRegex(ValueError, "secret query parameters"):
            self.build_metadata(source_url="https://example.go.kr/api?serviceKey=do-not-store")

    def test_rejects_path_as_original_filename(self) -> None:
        with self.assertRaisesRegex(ValueError, "basename"):
            self.build_metadata(original_filename="downloads/notice.pdf")

    def test_all_required_review_states_are_stable(self) -> None:
        self.assertEqual(
            {status.value for status in RawPolicyStatus},
            {"COLLECTED", "EXTRACTED", "REVIEWING", "APPROVED", "REJECTED", "OUTDATED"},
        )


class RawPolicyHashTests(unittest.TestCase):
    def test_hashes_exact_original_bytes(self) -> None:
        self.assertEqual(
            sha256_bytes(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )
