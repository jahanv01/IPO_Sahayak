"""Re-ranks vector-search candidates with a cross-encoder for better relevance ordering.

Bi-encoder search (embeddings.py + pgvector) is fast but approximate — it scores the
query and each chunk independently. A cross-encoder scores the (query, chunk) pair
jointly, which is slower but more accurate, so it's used only to re-rank the small
candidate set the vector search already narrowed down. Free, local, CPU — same pattern
as embeddings.py, no separate torch dependency.
"""

from __future__ import annotations

from fastembed.rerank.cross_encoder import TextCrossEncoder

MODEL_NAME = "Xenova/ms-marco-MiniLM-L-6-v2"

_model: TextCrossEncoder | None = None


def _get_model() -> TextCrossEncoder:
    global _model
    if _model is None:
        _model = TextCrossEncoder(model_name=MODEL_NAME)
    return _model


def rerank(query: str, documents: list[str], top_k: int) -> list[int]:
    """Return the indices of the top_k documents, best match first."""
    if not documents:
        return []
    model = _get_model()
    scores = list(model.rerank(query, documents))
    ranked = sorted(range(len(documents)), key=lambda i: scores[i], reverse=True)
    return ranked[:top_k]
