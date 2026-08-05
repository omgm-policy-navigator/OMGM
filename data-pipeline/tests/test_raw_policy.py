import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

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
            "collection_id": "collection-001",
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
        result = self.build_metadata(
            status=RawPolicyStatus.REVIEWING,
            status_updated_at=datetime(2026, 8, 5, 4, 0, tzinfo=timezone.utc),
        ).to_dict()

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
        self.assertIn(metadata.content_sha256, content_path.as_posix())
        self.assertIn(metadata.collection_id, content_path.as_posix())

    def test_different_collection_events_do_not_share_sidecar_path(self) -> None:
        first = self.build_metadata(
            collection_id="collection-001",
            source_url="https://agency-a.go.kr/notice/1",
        )
        second = self.build_metadata(
            collection_id="collection-002",
            source_url="https://agency-b.go.kr/notice/2",
        )

        _, first_sidecar = raw_storage_paths(first, "sample-agency", "pdf")
        _, second_sidecar = raw_storage_paths(second, "sample-agency", "pdf")

        self.assertNotEqual(first_sidecar, second_sidecar)

    def test_rejects_non_utc_collection_time(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone-aware UTC"):
            self.build_metadata(collected_at=datetime(2026, 8, 5, 3, 4, 5))

    def test_rejects_any_query_or_fragment_in_source_url(self) -> None:
        for source_url in (
            "https://example.go.kr/api?page=1",
            "https://example.go.kr/notice#section",
        ):
            with self.subTest(source_url=source_url):
                with self.assertRaisesRegex(ValueError, "no query or fragment"):
                    self.build_metadata(source_url=source_url)

    def test_rejects_enum_strings_at_construction(self) -> None:
        for field_name, value, expected_message in (
            ("source_authority", "OFFICIAL", "source_authority must be SourceAuthority"),
            ("source_format", "PDF", "source_format must be SourceFormat"),
            ("status", "COLLECTED", "status must be RawPolicyStatus"),
        ):
            with self.subTest(field_name=field_name):
                with self.assertRaisesRegex(TypeError, expected_message):
                    self.build_metadata(**{field_name: value})

    def test_requires_status_timestamp_after_collection(self) -> None:
        with self.assertRaisesRegex(ValueError, "status_updated_at is required"):
            self.build_metadata(status=RawPolicyStatus.APPROVED)

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


class RawPolicyJsonSchemaContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        schema_path = Path(__file__).parents[1] / "schemas" / "raw-policy.schema.json"
        cls.schema = json.loads(schema_path.read_text(encoding="utf-8"))

    def test_python_serialization_keys_match_json_schema(self) -> None:
        metadata = RawPolicyMetadataTests().build_metadata().to_dict()

        self.assertEqual(set(metadata), set(self.schema["properties"]))
        self.assertTrue(set(self.schema["required"]).issubset(metadata))

    def test_python_enums_match_json_schema(self) -> None:
        self.assertEqual(
            {value.value for value in SourceAuthority},
            set(self.schema["properties"]["source_authority"]["enum"]),
        )
        self.assertEqual(
            {value.value for value in SourceFormat},
            set(self.schema["properties"]["source_format"]["enum"]),
        )
        self.assertEqual(
            {value.value for value in RawPolicyStatus},
            set(self.schema["properties"]["status"]["enum"]),
        )
