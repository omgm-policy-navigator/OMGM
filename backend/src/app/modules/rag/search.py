from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.modules.rag.embedding import EmbeddingProvider


@dataclass(frozen=True)
class SearchHit:
    chunk_id: str
    document_id: str
    policy_id: str
    policy_version: str
    title: str
    content: str
    source_url: str
    source_location: str
    chunk_type: str
    similarity: float


@dataclass(frozen=True)
class Citation:
    source_id: str
    evidence_id: str
    policy_version_id: str
    title: str
    url: str
    source_location: str
    excerpt: str
    similarity: float


@dataclass(frozen=True)
class RagSearchResult:
    citations: tuple[Citation, ...]
    insufficient_evidence: bool


class RagSearchRepository(Protocol):
    async def search(
        self,
        *,
        policy_id: str,
        embedding: tuple[float, ...],
        model: str,
        top_k: int,
        minimum_similarity: float,
    ) -> tuple[SearchHit, ...]: ...


async def search_policy_evidence(
    *,
    policy_id: str,
    question: str,
    provider: EmbeddingProvider,
    repository: RagSearchRepository,
    top_k: int = 5,
    minimum_similarity: float = 0.55,
) -> RagSearchResult:
    if not policy_id.strip() or not question.strip():
        raise ValueError("policy_id and question must not be blank")
    if not 1 <= top_k <= 20:
        raise ValueError("top_k must be between 1 and 20")
    if not 0 <= minimum_similarity <= 1:
        raise ValueError("minimum_similarity must be between 0 and 1")
    embedding = (await provider.embed((question,)))[0]
    hits = await repository.search(
        policy_id=policy_id,
        embedding=embedding,
        model=provider.model,
        top_k=top_k,
        minimum_similarity=minimum_similarity,
    )
    citations = tuple(
        Citation(
            source_id=hit.document_id,
            evidence_id=hit.chunk_id,
            policy_version_id=hit.policy_version,
            title=hit.title,
            url=hit.source_url,
            source_location=hit.source_location,
            excerpt=hit.content[:500],
            similarity=hit.similarity,
        )
        for hit in hits
    )
    return RagSearchResult(citations=citations, insufficient_evidence=not citations)
