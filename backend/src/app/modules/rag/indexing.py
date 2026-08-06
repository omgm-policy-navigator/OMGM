from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from app.modules.rag.document_processing import EmbeddingSeed
from app.modules.rag.embedding import EmbeddingProvider


class RagChunkType(StrEnum):
    OVERVIEW = "OVERVIEW"
    ELIGIBILITY = "ELIGIBILITY"
    APPLICATION = "APPLICATION"
    DOCUMENTS = "DOCUMENTS"
    FAQ = "FAQ"
    CAUTION = "CAUTION"


def retrieval_chunk_type(seed: EmbeddingSeed) -> RagChunkType:
    if seed.document_type.value == "FAQ":
        return RagChunkType.FAQ
    mapping = {
        "ELIGIBILITY": RagChunkType.ELIGIBILITY,
        "APPLICATION_PERIOD": RagChunkType.APPLICATION,
        "APPLICATION_METHOD": RagChunkType.APPLICATION,
        "REQUIRED_DOCUMENTS": RagChunkType.DOCUMENTS,
        "CONTACT": RagChunkType.CAUTION,
    }
    return mapping.get(seed.chunk_kind.value, RagChunkType.OVERVIEW)


@dataclass(frozen=True)
class IndexableChunk:
    chunk_id: str
    document_id: str
    policy_id: str
    policy_version: str
    policy_status: str
    document_status: str
    trust_level: str
    document_type: str
    chunk_type: str
    title: str
    content: str
    source_url: str
    source_location: str
    content_hash: str
    embedding: tuple[float, ...]
    embedding_model: str


class ChunkIndexRepository(Protocol):
    async def delete_documents_not_in(self, document_ids: set[str]) -> None: ...

    async def replace_document_chunks(self, document_id: str, chunks: tuple[IndexableChunk, ...]) -> None: ...


async def reindex_document(
    *,
    seeds: tuple[EmbeddingSeed, ...],
    policy_version: str,
    policy_status: str,
    document_status: str,
    trust_level: str,
    provider: EmbeddingProvider,
    repository: ChunkIndexRepository,
) -> int:
    if not seeds:
        return 0
    document_ids = {seed.document_id for seed in seeds}
    if len(document_ids) != 1:
        raise ValueError("one reindex operation must target exactly one document")
    if document_status != "APPROVED" or trust_level != "OFFICIAL" or policy_status != "ACTIVE":
        raise ValueError("only approved official documents for active policies can be indexed")
    embeddings = await provider.embed(tuple(f"{seed.heading}\n{seed.content}" for seed in seeds))
    chunks = tuple(
        IndexableChunk(
            chunk_id=seed.chunk_id,
            document_id=seed.document_id,
            policy_id=seed.policy_id,
            policy_version=policy_version,
            policy_status=policy_status,
            document_status=document_status,
            trust_level=trust_level,
            document_type=seed.document_type.value,
            chunk_type=retrieval_chunk_type(seed).value,
            title=seed.heading,
            content=seed.content,
            source_url=seed.source_url,
            source_location=seed.source_location,
            content_hash=seed.content_hash,
            embedding=embeddings[index],
            embedding_model=provider.model,
        )
        for index, seed in enumerate(seeds)
    )
    await repository.replace_document_chunks(next(iter(document_ids)), chunks)
    return len(chunks)
