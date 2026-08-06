from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

import httpx

EMBEDDING_DIMENSIONS = 1024


class EmbeddingError(RuntimeError):
    pass


class EmbeddingProvider(Protocol):
    model: str

    async def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]: ...


@dataclass
class OllamaEmbeddingProvider:
    base_url: str
    model: str = "qwen3-embedding:0.6b"
    timeout_seconds: float = 30
    client: httpx.AsyncClient | None = None

    async def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        if not texts or any(not text.strip() for text in texts):
            raise EmbeddingError("embedding input must contain non-blank text")
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(
            base_url=self.base_url.rstrip("/"), timeout=httpx.Timeout(self.timeout_seconds)
        )
        try:
            response = await client.post("/api/embed", json={"model": self.model, "input": list(texts)})
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise EmbeddingError("Ollama embedding request failed") from exc
        finally:
            if owns_client:
                await client.aclose()

        raw_embeddings = payload.get("embeddings")
        if not isinstance(raw_embeddings, list) or len(raw_embeddings) != len(texts):
            raise EmbeddingError("Ollama returned an invalid embedding count")
        embeddings = tuple(tuple(float(value) for value in vector) for vector in raw_embeddings)
        if any(len(vector) != EMBEDDING_DIMENSIONS for vector in embeddings):
            raise EmbeddingError(f"embedding dimension must be {EMBEDDING_DIMENSIONS}")
        if any(not math.isfinite(value) for vector in embeddings for value in vector):
            raise EmbeddingError("embedding values must be finite")
        return embeddings
