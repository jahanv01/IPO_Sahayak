"""Generates a grounded, cited answer from a question and a handful of DRHP excerpts.

Training-free substitute for RAFT (retrieval-augmented fine-tuning): instead of
fine-tuning a model to ignore irrelevant retrieved passages, the system prompt tells it
explicitly that some excerpts may be distractors and to cite only the ones it actually
used. Grounding through prompting, not weights.

Uses the Gemini API (free tier) rather than Claude: no billing/card needed to develop
and test this epic. generate_answer(question, chunks) keeps a stable signature so the
model/provider behind it can be swapped later (e.g. a self-hosted RAFT-tuned model)
without touching retrieval.py or ask.py.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.db import RetrievedChunk

MODEL_FLASH = "gemini-flash-latest"
MODEL_PRO = "gemini-pro-latest"
# "-latest" aliases rather than dated model IDs: Google deprecates dated Gemini models for
# new API keys fairly quickly (gemini-2.5-flash, current at write time, already 404s on a
# fresh key), and the alias insulates this code from that churn.
# Flash for all development/testing (free tier, fast); switch to Pro for demo polish
# via the GEMINI_MODEL env var — generate_answer's signature never changes either way.
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", MODEL_FLASH)

SYSTEM_PROMPT = """You are IPO Sahayak, an assistant that helps first-time Indian investors \
understand IPO prospectus documents (DRHPs). You answer questions using ONLY the excerpts \
provided in the user's message — never your own knowledge of the company, the market, or \
general financial facts.

Grounding rules:
- Base your answer strictly on the provided excerpts. Do not add outside information, even \
if you believe it to be true.
- Some of the excerpts were retrieved automatically and may be irrelevant distractors that \
don't actually address the question. Judge each one on its merits; ignore and do not cite \
any excerpt that doesn't genuinely support your answer.
- If none of the excerpts actually answer the question, set not_mentioned to true and say so \
plainly in the answer — do not guess or infer.
- Every claim in your answer must be backed by at least one citation with a short verbatim \
quote copied exactly (not paraphrased) from the excerpt that supports it.
- Write for someone with zero investing background: plain language, no jargon.

Safety rule:
- You are an educational tool, not a financial advisor. Never recommend that the user buy, \
sell, hold, or avoid this or any investment, and never state or imply what they should do. \
Only describe what the document says — the investment decision is entirely the user's."""


class _CitationSchema(BaseModel):
    chunk_number: int = Field(description="The numbered excerpt (1-based) this citation refers to.")
    quote: str = Field(
        description=(
            "A short verbatim quote (under 30 words) copied exactly from that "
            "excerpt supporting the claim."
        )
    )


class _AnswerSchema(BaseModel):
    not_mentioned: bool = Field(
        description=(
            "True if the provided excerpts do not contain information to answer the question."
        )
    )
    answer: str = Field(
        description=(
            "The answer in plain language for a first-time investor. If not_mentioned "
            "is true, a brief note that this isn't covered in the provided excerpts."
        )
    )
    citations: list[_CitationSchema] = Field(
        default_factory=list, description="Supporting citations. Empty if not_mentioned is true."
    )


_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


@dataclass
class Citation:
    chunk_number: int
    quote: str
    verified: bool


@dataclass
class AnswerResult:
    answer: str
    not_mentioned: bool
    citations: list[Citation]
    model: str


def _format_chunks(chunks: list[RetrievedChunk]) -> str:
    parts = []
    for index, chunk in enumerate(chunks, start=1):
        page = f"page {chunk.page_number}" if chunk.page_number else "page unknown"
        parts.append(f"[Excerpt {index} — section: {chunk.section}, {page}]\n{chunk.content}")
    return "\n\n".join(parts)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def verify_citations(citations: list[Citation], chunks: list[RetrievedChunk]) -> None:
    """Confirm each citation's quote actually appears in the chunk it claims to cite.

    Mutates each Citation's `verified` flag in place. A citation whose quote can't be
    found in its source chunk is flagged rather than trusted — NFR-03 (never invent
    facts) means an unverifiable citation is treated as suspect, not silently shown.
    """
    by_number = {index: chunk for index, chunk in enumerate(chunks, start=1)}
    for citation in citations:
        chunk = by_number.get(citation.chunk_number)
        citation.verified = chunk is not None and _normalize(citation.quote) in _normalize(
            chunk.content
        )


def _refused(model: str) -> AnswerResult:
    return AnswerResult(
        answer="Unable to answer this question.",
        not_mentioned=True,
        citations=[],
        model=model,
    )


def generate_answer(
    question: str, chunks: list[RetrievedChunk], model: str = DEFAULT_MODEL
) -> AnswerResult:
    client = _get_client()
    user_content = f"Excerpts from the DRHP:\n\n{_format_chunks(chunks)}\n\nQuestion: {question}"

    response = client.models.generate_content(
        model=model,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_json_schema=_AnswerSchema.model_json_schema(),
        ),
    )

    candidates = response.candidates or []
    if not candidates:
        return _refused(model)

    finish_reason = getattr(candidates[0], "finish_reason", None)
    finish_reason_name = getattr(finish_reason, "name", finish_reason)
    if finish_reason_name not in ("STOP", None):
        return _refused(model)

    data = _AnswerSchema.model_validate_json(response.text)
    citations = [
        Citation(chunk_number=c.chunk_number, quote=c.quote, verified=False) for c in data.citations
    ]
    verify_citations(citations, chunks)

    return AnswerResult(
        answer=data.answer,
        not_mentioned=data.not_mentioned,
        citations=citations,
        model=model,
    )
