"""RAG document processing contracts."""

from app.modules.rag.document_processing import (
    ChunkKind,
    ChunkQuality,
    DocumentChunk,
    DocumentType,
    EmbeddingSeed,
    SourceDocument,
    build_embedding_seed,
    classify_document_type,
    process_document,
)
from app.modules.rag.embedding import EMBEDDING_DIMENSIONS, EmbeddingError, OllamaEmbeddingProvider
from app.modules.rag.indexing import IndexableChunk, RagChunkType, reindex_document, retrieval_chunk_type
from app.modules.rag.search import Citation, RagSearchResult, SearchHit, search_policy_evidence

__all__ = [
    "Citation",
    "ChunkKind",
    "ChunkQuality",
    "DocumentChunk",
    "DocumentType",
    "EMBEDDING_DIMENSIONS",
    "EmbeddingSeed",
    "EmbeddingError",
    "IndexableChunk",
    "OllamaEmbeddingProvider",
    "RagSearchResult",
    "RagChunkType",
    "SearchHit",
    "SourceDocument",
    "build_embedding_seed",
    "classify_document_type",
    "process_document",
    "reindex_document",
    "retrieval_chunk_type",
    "search_policy_evidence",
]
