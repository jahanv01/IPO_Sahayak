"""Generates embeddings for DRHP chunks using a free local model (no API cost)."""

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


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of chunk texts. Returns one 384-dim vector per input text."""
    if not texts:
        return []
    model = _get_model()
    return [vector.tolist() for vector in model.embed(texts)]
