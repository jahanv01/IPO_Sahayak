"""Unit tests for app/answer.py's grounding, citation, and verification logic.

Never calls the real Gemini API — client calls are mocked so CI doesn't burn API quota.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.answer import Citation, _format_chunks, _normalize, generate_answer, verify_citations
from app.db import RetrievedChunk


def make_chunk(
    chunk_id: int = 1,
    section: str = "Risk Factors",
    page: int | None = 12,
    content: str = "Some content here.",
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        company="Acme Ltd",
        section=section,
        page_number=page,
        content=content,
        distance=0.1,
    )


def test_format_chunks_numbers_and_labels_excerpts():
    chunks = [
        make_chunk(content="First chunk text."),
        make_chunk(section="Objects of the Issue", page=None, content="Second chunk text."),
    ]

    formatted = _format_chunks(chunks)

    assert "[Excerpt 1 — section: Risk Factors, page 12]\nFirst chunk text." in formatted
    assert (
        "[Excerpt 2 — section: Objects of the Issue, page unknown]\nSecond chunk text."
        in formatted
    )


def test_normalize_collapses_whitespace_and_case():
    assert _normalize("  Some   Text\n\nHere ") == "some text here"


def test_verify_citations_marks_matching_quote_verified():
    chunks = [make_chunk(content="The company reported revenue of Rs. 100 crore in FY23.")]
    citations = [Citation(chunk_number=1, quote="revenue of Rs. 100 crore", verified=False)]

    verify_citations(citations, chunks)

    assert citations[0].verified is True


def test_verify_citations_marks_unsupported_quote_unverified():
    chunks = [make_chunk(content="The company reported revenue of Rs. 100 crore in FY23.")]
    citations = [Citation(chunk_number=1, quote="profit margin improved sharply", verified=False)]

    verify_citations(citations, chunks)

    assert citations[0].verified is False


def test_verify_citations_marks_unknown_chunk_number_unverified():
    citations = [Citation(chunk_number=5, quote="anything", verified=False)]

    verify_citations(citations, [make_chunk()])

    assert citations[0].verified is False


def _mock_response(json_text: str, finish_reason: str | None = "STOP"):
    candidate = MagicMock()
    if finish_reason is None:
        candidate.finish_reason = None
    else:
        # Mimic the google-genai enum: an object with a .name attribute.
        reason = MagicMock()
        reason.name = finish_reason
        candidate.finish_reason = reason
    response = MagicMock()
    response.candidates = [candidate]
    response.text = json_text
    return response


def _mock_blocked_response():
    response = MagicMock()
    response.candidates = []
    return response


@patch("app.answer._get_client")
def test_generate_answer_returns_verified_citation(mock_get_client):
    chunk = make_chunk(content="The issue size is Rs. 500 crore.")
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _mock_response(
        '{"not_mentioned": false, "answer": "The issue size is Rs. 500 crore.", '
        '"citations": [{"chunk_number": 1, "quote": "issue size is Rs. 500 crore"}]}'
    )
    mock_get_client.return_value = mock_client

    result = generate_answer("What is the issue size?", [chunk], model="gemini-2.5-flash")

    assert result.not_mentioned is False
    assert result.answer == "The issue size is Rs. 500 crore."
    assert len(result.citations) == 1
    assert result.citations[0].verified is True
    assert result.model == "gemini-2.5-flash"

    _, kwargs = mock_client.models.generate_content.call_args
    assert kwargs["model"] == "gemini-2.5-flash"
    assert kwargs["config"].response_mime_type == "application/json"


@patch("app.answer._get_client")
def test_generate_answer_flags_unverifiable_citation(mock_get_client):
    chunk = make_chunk(content="The issue size is Rs. 500 crore.")
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _mock_response(
        '{"not_mentioned": false, "answer": "The issue size is Rs. 900 crore.", '
        '"citations": [{"chunk_number": 1, "quote": "issue size is Rs. 900 crore"}]}'
    )
    mock_get_client.return_value = mock_client

    result = generate_answer("What is the issue size?", [chunk])

    assert result.citations[0].verified is False


@patch("app.answer._get_client")
def test_generate_answer_reports_not_mentioned(mock_get_client):
    chunk = make_chunk(content="Nothing about dividends here.")
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _mock_response(
        '{"not_mentioned": true, "answer": "Dividend policy isn\'t covered.", "citations": []}'
    )
    mock_get_client.return_value = mock_client

    result = generate_answer("What is the dividend policy?", [chunk])

    assert result.not_mentioned is True
    assert result.citations == []


@patch("app.answer._get_client")
def test_generate_answer_handles_blocked_response(mock_get_client):
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _mock_blocked_response()
    mock_get_client.return_value = mock_client

    result = generate_answer("anything", [make_chunk()])

    assert result.not_mentioned is True
    assert result.citations == []
    assert result.answer


@patch("app.answer._get_client")
def test_generate_answer_handles_non_stop_finish_reason(mock_get_client):
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _mock_response(
        "", finish_reason="PROHIBITED_CONTENT"
    )
    mock_get_client.return_value = mock_client

    result = generate_answer("anything", [make_chunk()])

    assert result.not_mentioned is True
    assert result.citations == []
