import unittest

from app.modules.rag import (
    ChunkKind,
    ChunkQuality,
    DocumentType,
    SourceDocument,
    build_embedding_seed,
    classify_document_type,
    process_document,
)
from app.modules.rag.document_processing import DocumentProcessingError


class RagDocumentProcessingTests(unittest.TestCase):
    def source(self, content: str, title: str = "신혼 지원 공고") -> SourceDocument:
        return SourceDocument(
            document_id="doc_test_1",
            policy_id="policy_test_1",
            title=title,
            content=content,
            source_url="https://example.go.kr/policies/test-1",
        )

    def test_document_type_is_classified_from_title(self) -> None:
        self.assertEqual(classify_document_type("2026년 모집 공고"), DocumentType.OFFICIAL_NOTICE)
        self.assertEqual(classify_document_type("신청 안내"), DocumentType.APPLICATION_GUIDE)
        self.assertEqual(classify_document_type("자주 묻는 질문 FAQ"), DocumentType.FAQ)
        self.assertEqual(classify_document_type("정책 개요"), DocumentType.OVERVIEW)

    def test_headings_keep_eligibility_and_application_method_separate(self) -> None:
        chunks = process_document(
            self.source(
                """# 신청 대상
서울 거주 무주택 신혼부부가 신청할 수 있습니다.

# 신청 방법
공식 누리집에서 온라인 신청합니다."""
            )
        )

        self.assertEqual([chunk.chunk_kind for chunk in chunks], [ChunkKind.ELIGIBILITY, ChunkKind.APPLICATION_METHOD])
        self.assertNotEqual(chunks[0].source_location, chunks[1].source_location)
        self.assertTrue(all(chunk.source_url.startswith("https://") for chunk in chunks))

    def test_article_heading_becomes_source_location(self) -> None:
        chunks = process_document(self.source("제1조(지원대상)\n서울 거주 신혼부부를 지원합니다."))

        self.assertIn("제1조(지원대상)", chunks[0].source_location)
        self.assertEqual(chunks[0].chunk_kind, ChunkKind.ELIGIBILITY)

    def test_markdown_table_is_split_into_one_chunk_per_data_row(self) -> None:
        chunks = process_document(
            self.source(
                """# 지원 내용
| 구분 | 내용 |
| --- | --- |
| 지원금 | 최대 100만원 |
| 지급방식 | 계좌 지급 |"""
            )
        )

        self.assertEqual(len(chunks), 2)
        self.assertTrue(all(chunk.chunk_kind is ChunkKind.TABLE_ROW for chunk in chunks))
        self.assertIn("table:1/row:1", chunks[0].source_location)
        self.assertIn("구분: 지원금", chunks[0].content)

    def test_mixed_semantic_sentence_requires_quality_review(self) -> None:
        chunks = process_document(self.source("신청 대상 요건을 확인하고 신청 방법에 따라 접수합니다."))

        self.assertEqual(chunks[0].quality, ChunkQuality.REVIEW_REQUIRED)
        self.assertIn("mixed_semantic_kinds", chunks[0].quality_issues)
        with self.assertRaises(DocumentProcessingError):
            build_embedding_seed(chunks)

    def test_sentences_with_different_meanings_are_split(self) -> None:
        chunks = process_document(
            self.source("신청 대상은 서울 거주 신혼부부입니다. 신청 방법은 공식 누리집 온라인 접수입니다.")
        )

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].chunk_kind, ChunkKind.ELIGIBILITY)
        self.assertEqual(chunks[1].chunk_kind, ChunkKind.APPLICATION_METHOD)
        self.assertTrue(all(chunk.quality is ChunkQuality.APPROVED for chunk in chunks))

    def test_embedding_seed_preserves_policy_and_provenance(self) -> None:
        chunks = process_document(self.source("정책 지원 내용을 안내합니다.", title="정책 개요"))

        seed = build_embedding_seed(chunks)

        self.assertEqual(seed[0].policy_id, "policy_test_1")
        self.assertEqual(seed[0].document_id, "doc_test_1")
        self.assertEqual(seed[0].source_url, "https://example.go.kr/policies/test-1")
        self.assertTrue(seed[0].source_location)
        self.assertEqual(len(seed[0].content_hash), 64)

    def test_contact_chunk_requires_review_before_embedding(self) -> None:
        chunks = process_document(self.source("문의: 담당부서 업무 연락처를 확인하세요."))

        self.assertEqual(chunks[0].chunk_kind, ChunkKind.CONTACT)
        self.assertEqual(chunks[0].quality, ChunkQuality.REVIEW_REQUIRED)
        self.assertIn("contact_requires_review", chunks[0].quality_issues)

    def test_invalid_source_url_and_empty_document_are_rejected(self) -> None:
        with self.assertRaises(DocumentProcessingError):
            SourceDocument("doc", "policy", "title", "content", "file:///policy.txt")
        with self.assertRaises(DocumentProcessingError):
            self.source("   ")
