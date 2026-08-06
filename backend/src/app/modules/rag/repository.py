from __future__ import annotations

from sqlalchemy import delete, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.models import DocumentChunk
from app.modules.rag.indexing import IndexableChunk
from app.modules.rag.search import SearchHit


def _vector_literal(vector: tuple[float, ...]) -> str:
    return "[" + ",".join(format(value, ".17g") for value in vector) + "]"


class SqlAlchemyChunkIndexRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_document_chunks(self, document_id: str, chunks: tuple[IndexableChunk, ...]) -> None:
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        await self._session.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.id.not_in(chunk_ids),
            )
        )
        for chunk in chunks:
            values = {
                "id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "policy_id": chunk.policy_id,
                "policy_version": chunk.policy_version,
                "policy_status": chunk.policy_status,
                "document_status": chunk.document_status,
                "trust_level": chunk.trust_level,
                "document_type": chunk.document_type,
                "chunk_type": chunk.chunk_type,
                "title": chunk.title,
                "content": chunk.content,
                "source_url": chunk.source_url,
                "source_location": chunk.source_location,
                "content_hash": chunk.content_hash,
            }
            statement = insert(DocumentChunk).values(**values)
            statement = statement.on_conflict_do_update(
                index_elements=[DocumentChunk.id],
                set_={key: statement.excluded[key] for key in values if key != "id"},
            )
            await self._session.execute(statement)
            await self._session.execute(
                text(
                    """
                    INSERT INTO document_chunk_embedding (chunk_id, model, embedding)
                    VALUES (:chunk_id, :model, CAST(:embedding AS vector))
                    ON CONFLICT (chunk_id, model) DO UPDATE
                    SET embedding = EXCLUDED.embedding, created_at = now()
                    """
                ),
                {
                    "chunk_id": chunk.chunk_id,
                    "model": chunk.embedding_model,
                    "embedding": _vector_literal(chunk.embedding),
                },
            )
        await self._session.commit()


class SqlAlchemyRagSearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(
        self,
        *,
        policy_id: str,
        embedding: tuple[float, ...],
        model: str,
        top_k: int,
        minimum_similarity: float,
    ) -> tuple[SearchHit, ...]:
        result = await self._session.execute(
            text(
                """
                SELECT dc.id AS chunk_id, dc.document_id, dc.policy_id, dc.policy_version,
                       dc.title, dc.content, dc.source_url, dc.source_location, dc.chunk_type,
                       1 - (dce.embedding <=> CAST(:embedding AS vector)) AS similarity
                FROM document_chunk AS dc
                JOIN document_chunk_embedding AS dce ON dce.chunk_id = dc.id
                WHERE dc.policy_id = :policy_id
                  AND dc.document_status = 'APPROVED'
                  AND dc.trust_level = 'OFFICIAL'
                  AND dc.policy_status = 'ACTIVE'
                  AND dce.model = :model
                  AND 1 - (dce.embedding <=> CAST(:embedding AS vector)) >= :minimum_similarity
                ORDER BY dce.embedding <=> CAST(:embedding AS vector), dc.id
                LIMIT :top_k
                """
            ),
            {
                "policy_id": policy_id,
                "embedding": _vector_literal(embedding),
                "model": model,
                "minimum_similarity": minimum_similarity,
                "top_k": top_k,
            },
        )
        return tuple(SearchHit(**dict(row)) for row in result.mappings())
