"""Unit tests for app/reranker.py's ranking logic.

The cross-encoder model itself is mocked out — tests only exercise the sort/slice logic,
not fastembed's actual model download/inference (kept out of CI for speed and determinism).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.reranker import rerank


def test_rerank_returns_empty_for_no_documents():
    assert rerank("a question", [], top_k=5) == []


@patch("app.reranker._get_model")
def test_rerank_orders_by_score_descending(mock_get_model):
    mock_model = MagicMock()
    mock_model.rerank.return_value = [0.1, 0.9, 0.5]
    mock_get_model.return_value = mock_model

    result = rerank("a question", ["low", "high", "mid"], top_k=3)

    assert result == [1, 2, 0]


@patch("app.reranker._get_model")
def test_rerank_truncates_to_top_k(mock_get_model):
    mock_model = MagicMock()
    mock_model.rerank.return_value = [0.2, 0.8, 0.6, 0.4]
    mock_get_model.return_value = mock_model

    result = rerank("a question", ["a", "b", "c", "d"], top_k=2)

    assert result == [1, 2]
