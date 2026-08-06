from __future__ import annotations

import asyncio
import csv
from collections import defaultdict
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import AppConfig
from app.db.session import create_engine
from app.modules.rag.document_processing import ChunkKind, DocumentType, EmbeddingSeed
from app.modules.rag.embedding import OllamaEmbeddingProvider
from app.modules.rag.indexing import reindex_document
from app.modules.rag.repository import SqlAlchemyChunkIndexRepository


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def load_approved_seed_documents(seed_directory: Path) -> dict[str, tuple[EmbeddingSeed, ...]]:
    policies = {row["id"]: row for row in _read_rows(seed_directory / "02_policy.csv")}
    grouped: dict[str, list[EmbeddingSeed]] = defaultdict(list)
    for row in _read_rows(seed_directory / "10_policy_document_chunk.csv"):
        policy = policies.get(row["policy_id"])
        if row["quality_status"] != "APPROVED" or policy is None or policy["status"] != "ACTIVE":
            continue
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
    return {document_id: tuple(chunks) for document_id, chunks in grouped.items()}


async def run() -> int:
    config = AppConfig.from_env()
    engine = create_engine(config.database_url, config.database_pool_size, config.database_max_overflow)
    provider = OllamaEmbeddingProvider(
        base_url=config.ollama_base_url,
        model=config.ollama_embedding_model,
        timeout_seconds=config.llm_timeout_seconds,
    )
    documents = load_approved_seed_documents(config.policy_seed_dir)
    policies = {row["id"]: row for row in _read_rows(config.policy_seed_dir / "02_policy.csv")}
    indexed = 0
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            repository = SqlAlchemyChunkIndexRepository(session)
            for seeds in documents.values():
                policy = policies[seeds[0].policy_id]
                indexed += await reindex_document(
                    seeds=seeds,
                    policy_version=f"{policy['id']}:{policy['verified_at']}",
                    policy_status=policy["status"],
                    document_status="APPROVED",
                    trust_level="OFFICIAL",
                    provider=provider,
                    repository=repository,
                )
    finally:
        await engine.dispose()
    return indexed


def main() -> None:
    indexed = asyncio.run(run())
    print(f"indexed {indexed} approved RAG chunks")


if __name__ == "__main__":
    main()
