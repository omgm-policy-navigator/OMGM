from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.session import create_engine
from app.modules.rag.indexing import IndexableChunk
from app.modules.rag.repository import SqlAlchemyChunkIndexRepository, SqlAlchemyRagSearchRepository

DATABASE_URL = os.getenv("DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL is required for pgvector integration tests")


def vector(first: float, second: float) -> tuple[float, ...]:
    return (first, second, *([0.0] * 1022))


def chunk(chunk_id: str, document_id: str, embedding: tuple[float, ...], model: str) -> IndexableChunk:
    return IndexableChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        policy_id="rag_it_policy",
        policy_version="rag_it_policy:2026-08-06",
        policy_status="ACTIVE",
        document_status="APPROVED",
        trust_level="OFFICIAL",
        document_type="OVERVIEW",
        chunk_type="OVERVIEW",
        title=chunk_id,
        content=f"integration evidence {chunk_id}",
        source_url=f"https://example.go.kr/{chunk_id}",
        source_location=f"section:{chunk_id}",
        content_hash=("a" if chunk_id.endswith("1") else "b") * 64,
        embedding=embedding,
        embedding_model=model,
    )


def test_pgvector_insert_search_reindex_model_cleanup_and_cascade() -> None:
    asyncio.run(_run_pgvector_contract())


async def _run_pgvector_contract() -> None:
    assert DATABASE_URL is not None
    engine = create_engine(DATABASE_URL, pool_size=1, max_overflow=0)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        repository = SqlAlchemyChunkIndexRepository(session)
        try:
            await session.execute(text("DELETE FROM document_chunk WHERE policy_id = 'rag_it_policy'"))
            await repository.replace_document_chunks(
                "rag_it_doc",
                (
                    chunk("rag_it_chunk_1", "rag_it_doc", vector(1.0, 0.0), "old-model"),
                    chunk("rag_it_chunk_2", "rag_it_doc", vector(0.0, 1.0), "old-model"),
                ),
            )
            await repository.replace_document_chunks(
                "rag_it_doc",
                (
                    chunk("rag_it_chunk_1", "rag_it_doc", vector(1.0, 0.0), "active-model"),
                    chunk("rag_it_chunk_2", "rag_it_doc", vector(0.0, 1.0), "active-model"),
                ),
            )
            await session.commit()

            model_count = await session.scalar(
                text(
                    "SELECT count(*) FROM document_chunk_embedding "
                    "WHERE chunk_id = 'rag_it_chunk_1'"
                )
            )
            assert model_count == 1

            savepoint = await session.begin_nested()
            with pytest.raises(DBAPIError):
                await session.execute(
                    text(
                        "INSERT INTO document_chunk_embedding (chunk_id, model, embedding) "
                        "VALUES ('rag_it_chunk_1', 'invalid-dimension', CAST('[1,0]' AS vector))"
                    )
                )
            await savepoint.rollback()

            hits = await SqlAlchemyRagSearchRepository(session).search(
                policy_id="rag_it_policy",
                embedding=vector(1.0, 0.0),
                model="active-model",
                top_k=2,
                minimum_similarity=0.0,
            )
            assert [hit.chunk_id for hit in hits] == ["rag_it_chunk_1", "rag_it_chunk_2"]

            await repository.replace_document_chunks(
                "rag_it_doc",
                (chunk("rag_it_chunk_1", "rag_it_doc", vector(1.0, 0.0), "active-model"),),
            )
            await session.commit()
            stale_count = await session.scalar(
                text("SELECT count(*) FROM document_chunk WHERE id = 'rag_it_chunk_2'")
            )
            assert stale_count == 0

            await session.execute(text("DELETE FROM document_chunk WHERE id = 'rag_it_chunk_1'"))
            await session.commit()
            embedding_count = await session.scalar(
                text("SELECT count(*) FROM document_chunk_embedding WHERE chunk_id = 'rag_it_chunk_1'")
            )
            assert embedding_count == 0
        finally:
            await session.execute(text("DELETE FROM document_chunk WHERE policy_id = 'rag_it_policy'"))
            await session.commit()
    await engine.dispose()
