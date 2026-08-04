#!/usr/bin/env sh
set -eu

GENERATION_MODEL="${OLLAMA_GENERATION_MODEL:-qwen3:4b}"
EMBEDDING_MODEL="${OLLAMA_EMBEDDING_MODEL:-qwen3-embedding:0.6b}"

ollama pull "$GENERATION_MODEL"
ollama pull "$EMBEDDING_MODEL"
