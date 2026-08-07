"""Generates embeddings using the same free local model the pipeline indexed chunks with.

Deliberately duplicated from pipeline/embedder.py rather than imported: Render's Docker
build context is scoped to ./backend, so it can't see files outside this directory. The
model name and dimension must stay identical to whatever pipeline/embedder.py uses —
mismatched embedding spaces make cosine similarity search meaningless.
"""

from __future__ import annotations

from fastembed import TextEmbedding

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

_model: TextEmbedding | None = None


def _get_model() -> TextEmbedding:
    global _model
    if _model is None:
        _model = TextEmbedding(model_name=MODEL_NAME)
    return _model


def embed_query(text: str) -> list[float]:
    """Embed a single query string into a 384-dim vector."""
    model = _get_model()
    return next(model.embed([text])).tolist()
