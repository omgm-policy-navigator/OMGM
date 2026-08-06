from __future__ import annotations

import asyncio
import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import AppConfig
from app.db.session import create_engine
from app.modules.rag.document_processing import ChunkKind, DocumentType, EmbeddingSeed
from app.modules.rag.embedding import EmbeddingProvider, OllamaEmbeddingProvider
from app.modules.rag.indexing import ChunkIndexRepository, reindex_document
from app.modules.rag.repository import SqlAlchemyChunkIndexRepository


@dataclass(frozen=True)
class SeedDocumentBatch:
    seeds: tuple[EmbeddingSeed, ...]
    policy_version: str
    policy_status: str
    document_status: str
    trust_level: str


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def load_approved_seed_documents(seed_directory: Path) -> dict[str, SeedDocumentBatch]:
    policies = {row["id"]: row for row in _read_rows(seed_directory / "02_policy.csv")}
    documents = {row["id"]: row for row in _read_rows(seed_directory / "08_policy_document.csv")}
    grouped: dict[str, list[EmbeddingSeed]] = defaultdict(list)
    for row in _read_rows(seed_directory / "10_policy_document_chunk.csv"):
        policy = policies.get(row["policy_id"])
        document = documents.get(row["document_id"])
        if policy is None or document is None:
            continue
        if (
            policy["status"] != "ACTIVE"
            or document["document_status"] != "APPROVED"
            or document["trust_level"] != "OFFICIAL"
            or row["quality_status"] != "APPROVED"
        ):
            continue
        if document["policy_id"] != row["policy_id"]:
            raise ValueError(f"chunk {row['id']} policy does not match document")
        if document["document_type"] != row["document_type"]:
            raise ValueError(f"chunk {row['id']} type does not match document")
        if document["source_url"] != row["source_url"]:
            raise ValueError(f"chunk {row['id']} source URL does not match document")
        grouped[row["document_id"]].append(
            EmbeddingSeed(
                chunk_id=row["id"],
                policy_id=row["policy_id"],
                document_id=row["document_id"],
                document_type=DocumentType(row["document_type"]),
                chunk_kind=ChunkKind(row["chunk_kind"]),
                heading=row["heading"],
                content=row["content"],
                source_url=row["source_url"],
                source_location=row["source_location"],
                content_hash=row["content_hash"],
            )
        )
    return {
        document_id: SeedDocumentBatch(
            seeds=tuple(chunks),
            policy_version=f"{chunks[0].policy_id}:{policies[chunks[0].policy_id]['verified_at']}",
            policy_status=policies[chunks[0].policy_id]["status"],
            document_status=documents[document_id]["document_status"],
            trust_level=documents[document_id]["trust_level"],
        )
        for document_id, chunks in grouped.items()
    }


async def synchronize_index(
    documents: dict[str, SeedDocumentBatch],
    provider: EmbeddingProvider,
    repository: ChunkIndexRepository,
) -> int:
    await repository.delete_documents_not_in(set(documents))
    indexed = 0
    for batch in documents.values():
        indexed += await reindex_document(
            seeds=batch.seeds,
            policy_version=batch.policy_version,
            policy_status=batch.policy_status,
            document_status=batch.document_status,
            trust_level=batch.trust_level,
            provider=provider,
            repository=repository,
        )
    return indexed


async def run() -> int:
    config = AppConfig.from_env()
    engine = create_engine(config.database_url, config.database_pool_size, config.database_max_overflow)
    provider = OllamaEmbeddingProvider(
        base_url=config.ollama_base_url,
        model=config.ollama_embedding_model,
        timeout_seconds=config.llm_timeout_seconds,
    )
    documents = load_approved_seed_documents(config.policy_seed_dir)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            repository = SqlAlchemyChunkIndexRepository(session)
            try:
                indexed = await synchronize_index(documents, provider, repository)
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    finally:
        await engine.dispose()
    return indexed


def main() -> None:
    indexed = asyncio.run(run())
    print(f"indexed {indexed} approved RAG chunks")


if __name__ == "__main__":
    main()
