from __future__ import annotations

import asyncio
import csv
import shutil
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.modules.rag.document_processing import ChunkKind, DocumentType, EmbeddingSeed
from app.modules.rag.embedding import EMBEDDING_DIMENSIONS, EmbeddingError, OllamaEmbeddingProvider
from app.modules.rag.indexing import IndexableChunk, RagChunkType, reindex_document, retrieval_chunk_type
from app.modules.rag.reindex import load_approved_seed_documents, synchronize_index
from app.modules.rag.search import SearchHit, search_policy_evidence


def async_test(function: Any) -> Any:
    @wraps(function)
    def wrapper() -> None:
        asyncio.run(function())

    return wrapper


@dataclass
class FakeEmbeddingProvider:
    model: str = "qwen3-embedding:0.6b"
    calls: list[tuple[str, ...]] = field(default_factory=list)

    async def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        self.calls.append(texts)
        return tuple(tuple([0.1] * EMBEDDING_DIMENSIONS) for _ in texts)


@dataclass
class FakeIndexRepository:
    documents: dict[str, dict[str, IndexableChunk]] = field(default_factory=dict)

    async def delete_documents_not_in(self, document_ids: set[str]) -> None:
        self.documents = {
            document_id: chunks
            for document_id, chunks in self.documents.items()
            if document_id in document_ids
        }

    async def replace_document_chunks(self, document_id: str, chunks: tuple[IndexableChunk, ...]) -> None:
        self.documents[document_id] = {chunk.chunk_id: chunk for chunk in chunks}


@dataclass
class FakeSearchRepository:
    hits: tuple[SearchHit, ...]
    received: dict[str, object] = field(default_factory=dict)

    async def search(self, **kwargs: object) -> tuple[SearchHit, ...]:
        self.received = kwargs
        return self.hits


def seed(chunk_id: str = "chunk_1") -> EmbeddingSeed:
    return EmbeddingSeed(
        chunk_id=chunk_id,
        policy_id="policy_1",
        document_id="doc_1",
        document_type=DocumentType.OFFICIAL_NOTICE,
        chunk_kind=ChunkKind.ELIGIBILITY,
        heading="신청 대상",
        content="서울 거주 신혼부부가 신청할 수 있습니다.",
        source_url="https://example.go.kr/policy/1",
        source_location="신청 대상 > 1문단",
        content_hash="a" * 64,
    )


def test_retrieval_chunk_types_match_a3_contract() -> None:
    assert retrieval_chunk_type(seed()) is RagChunkType.ELIGIBILITY
    faq_seed = EmbeddingSeed(**{**seed().__dict__, "document_type": DocumentType.FAQ})
    assert retrieval_chunk_type(faq_seed) is RagChunkType.FAQ


def test_reviewed_d4_seed_is_loadable_for_reindexing() -> None:
    seed_directory = Path(__file__).resolve().parents[2] / "data" / "policy-seed"
    documents = load_approved_seed_documents(seed_directory)

    assert len(documents) == 28
    assert sum(len(batch.seeds) for batch in documents.values()) == 28
    assert all(chunk.source_location for batch in documents.values() for chunk in batch.seeds)


def _copy_rag_seed_files(target: Path) -> None:
    source = Path(__file__).resolve().parents[2] / "data" / "policy-seed"
    for filename in ("02_policy.csv", "08_policy_document.csv", "10_policy_document_chunk.csv"):
        shutil.copyfile(source / filename, target / filename)


def _change_first_document(target: Path, **changes: str) -> None:
    path = target / "08_policy_document.csv"
    with path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    rows[0].update(changes)
    with path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def test_unapproved_and_nonofficial_documents_are_not_loaded(tmp_path: Path) -> None:
    _copy_rag_seed_files(tmp_path)
    _change_first_document(tmp_path, document_status="REVIEW_REQUIRED")
    assert "1" not in load_approved_seed_documents(tmp_path)

    _change_first_document(tmp_path, document_status="APPROVED", trust_level="SECONDARY")
    assert "1" not in load_approved_seed_documents(tmp_path)


def test_chunk_parent_metadata_mismatch_is_rejected(tmp_path: Path) -> None:
    _copy_rag_seed_files(tmp_path)
    _change_first_document(tmp_path, source_url="https://example.go.kr/different")
    with pytest.raises(ValueError, match="source URL does not match"):
        load_approved_seed_documents(tmp_path)


@async_test
async def test_reindex_replaces_same_document_without_duplicates() -> None:
    provider = FakeEmbeddingProvider()
    repository = FakeIndexRepository()

    assert await reindex_document(
        seeds=(seed(),),
        policy_version="version_1",
        policy_status="ACTIVE",
        document_status="APPROVED",
        trust_level="OFFICIAL",
        provider=provider,
        repository=repository,
    ) == 1
    await reindex_document(
        seeds=(seed(),),
        policy_version="version_1",
        policy_status="ACTIVE",
        document_status="APPROVED",
        trust_level="OFFICIAL",
        provider=provider,
        repository=repository,
    )

    assert list(repository.documents["doc_1"]) == ["chunk_1"]
    assert repository.documents["doc_1"]["chunk_1"].source_location == "신청 대상 > 1문단"


@async_test
async def test_full_synchronization_deletes_removed_documents() -> None:
    repository = FakeIndexRepository(documents={"old-document": {}, "doc_1": {}})
    batch = next(
        iter(
            load_approved_seed_documents(
                Path(__file__).resolve().parents[2] / "data" / "policy-seed"
            ).values()
        )
    )
    await synchronize_index({"doc_1": batch}, FakeEmbeddingProvider(), repository)

    assert "old-document" not in repository.documents


@async_test
async def test_reindex_rejects_unapproved_or_nonofficial_documents() -> None:
    provider = FakeEmbeddingProvider()
    repository = FakeIndexRepository()

    with pytest.raises(ValueError):
        await reindex_document(
            seeds=(seed(),),
            policy_version="version_1",
            policy_status="ACTIVE",
            document_status="DRAFT",
            trust_level="OFFICIAL",
            provider=provider,
            repository=repository,
        )
    assert provider.calls == []


@async_test
async def test_policy_search_returns_citation_metadata_and_filter_arguments() -> None:
    hit = SearchHit(
        chunk_id="chunk_1",
        document_id="doc_1",
        policy_id="policy_1",
        policy_version="version_1",
        title="신청 대상",
        content="근거 문구",
        source_url="https://example.go.kr/policy/1",
        source_location="신청 대상 > 1문단",
        chunk_type="ELIGIBILITY",
        similarity=0.82,
    )
    repository = FakeSearchRepository((hit,))

    result = await search_policy_evidence(
        policy_id="policy_1",
        question="신청할 수 있나요?",
        provider=FakeEmbeddingProvider(),
        repository=repository,
        top_k=3,
        minimum_similarity=0.6,
    )

    assert result.insufficient_evidence is False
    assert result.citations[0].evidence_id == "chunk_1"
    assert result.citations[0].source_location == "신청 대상 > 1문단"
    assert repository.received["policy_id"] == "policy_1"
    assert repository.received["top_k"] == 3
    assert repository.received["minimum_similarity"] == 0.6


@async_test
async def test_policy_search_detects_insufficient_evidence() -> None:
    result = await search_policy_evidence(
        policy_id="policy_1",
        question="근거가 있나요?",
        provider=FakeEmbeddingProvider(),
        repository=FakeSearchRepository(()),
    )

    assert result.insufficient_evidence is True
    assert result.citations == ()


@async_test
async def test_ollama_embedding_provider_validates_dimension() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/embed"
        return httpx.Response(200, json={"embeddings": [[0.0] * (EMBEDDING_DIMENSIONS - 1)]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ollama:11434")
    provider = OllamaEmbeddingProvider(base_url="http://ollama:11434", client=client)
    with pytest.raises(EmbeddingError):
        await provider.embed(("질문",))
    await client.aclose()
