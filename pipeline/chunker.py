"""Splits DRHP page text into section-aware, size-bounded chunks.

Section detection is heuristic, not a full table-of-contents parse: a page is treated as
the start of a new section when one of its first few lines matches a known heading almost
by itself. Two guards keep this from tripping on the DRHP's own table of contents (which
lists every heading, with a trailing page number, in the first ~15 pages):
  - headings are only looked for after a front-matter buffer of pages
  - a candidate line is rejected if it ends with digits (a ToC entry's page number)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Canonical heading -> target section category, or None if it's just a boundary marker
# (content under it is discarded rather than folded into whichever target section came
# before it). Not exhaustive — covers the headings needed to reasonably bound the four
# sections this project cares about.
_SECTION_HEADINGS: dict[str, str | None] = {
    "FORWARD-LOOKING STATEMENTS": None,
    "SUMMARY OF THE OFFER DOCUMENT": None,
    "SUMMARY OF OFFER DOCUMENT": None,
    "RISK FACTORS": "risk_factors",
    "OBJECTS OF THE OFFER": "objects_of_issue",
    "OBJECTS OF THE ISSUE": "objects_of_issue",
    "INDUSTRY OVERVIEW": None,
    "OUR BUSINESS": "business",
    "BUSINESS OVERVIEW": "business",
    "OUR HISTORY": None,
    "OUR MANAGEMENT": None,
    "OUR PROMOTERS": None,
    "FINANCIAL STATEMENTS": "financials",
    "RESTATED FINANCIAL STATEMENTS": "financials",
    "FINANCIAL INFORMATION": "financials",
    "MANAGEMENT'S DISCUSSION AND ANALYSIS": None,
    "OUTSTANDING LITIGATION": None,
    "GOVERNMENT AND OTHER APPROVALS": None,
    "OTHER REGULATORY AND STATUTORY DISCLOSURES": None,
    "TERMS OF THE OFFER": None,
    "TERMS OF THE ISSUE": None,
}

_TOC_BUFFER_PAGES = 15
_TRAILING_DIGITS_RE = re.compile(r"\d+\s*$")

# ~150 words keeps a chunk comfortably under all-MiniLM-L6-v2's 256-token limit
# (roughly 1.3 tokens/word for this kind of text) without relying on silent truncation.
DEFAULT_WORDS_PER_CHUNK = 150
DEFAULT_OVERLAP_WORDS = 30


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip().upper()


# How much slack to allow around a heading for prefixes like "SECTION II: " — wide
# enough for that, narrow enough to reject a heading's words appearing mid-sentence
# in ordinary prose (e.g. a bullet point that happens to start "Our business is...").
_HEADING_PREFIX_SLACK = 25


def _find_heading(page_text: str) -> str | None:
    """Return the canonical heading key if this page opens with a section heading.

    Real DRHPs prefix headings ("SECTION II: RISK FACTORS") and PyMuPDF often extracts
    a running page number as the page's own first line, so the first several lines are
    checked rather than just the first one.
    """
    lines = [_normalize_line(line) for line in page_text.splitlines()[:6] if line.strip()]
    for line in lines:
        if _TRAILING_DIGITS_RE.search(line):
            continue  # looks like a ToC entry ("RISK FACTORS ... 45"), not a heading
        for heading in _SECTION_HEADINGS:
            if heading in line and len(line) <= len(heading) + _HEADING_PREFIX_SLACK:
                return heading
    return None


@dataclass
class SectionedPage:
    page_number: int  # 1-indexed
    section: str  # target category, e.g. "risk_factors"
    text: str


def detect_sections(pages: list[str]) -> list[SectionedPage]:
    """Tag each page with the target section it belongs to, skipping front matter."""
    tagged: list[SectionedPage] = []
    current_section: str | None = None
    for index, text in enumerate(pages):
        if index >= _TOC_BUFFER_PAGES:
            heading = _find_heading(text)
            if heading is not None:
                current_section = _SECTION_HEADINGS[heading]
        if current_section is not None and text.strip():
            tagged.append(SectionedPage(page_number=index + 1, section=current_section, text=text))
    return tagged


@dataclass
class Chunk:
    section: str
    page_number: int  # page the chunk starts on
    chunk_index: int
    content: str


def build_chunks(
    sectioned_pages: list[SectionedPage],
    words_per_chunk: int = DEFAULT_WORDS_PER_CHUNK,
    overlap_words: int = DEFAULT_OVERLAP_WORDS,
) -> list[Chunk]:
    """Group pages by section, then split each section into overlapping word windows."""
    by_section: dict[str, list[SectionedPage]] = {}
    for page in sectioned_pages:
        by_section.setdefault(page.section, []).append(page)

    chunks: list[Chunk] = []
    step = max(words_per_chunk - overlap_words, 1)

    for section, section_pages in by_section.items():
        # Flatten to a (word, page_number) stream so a chunk can span pages without
        # losing which page it actually started on.
        words_with_pages: list[tuple[str, int]] = [
            (word, page.page_number) for page in section_pages for word in page.text.split()
        ]

        chunk_index = 0
        start = 0
        while start < len(words_with_pages):
            window = words_with_pages[start : start + words_per_chunk]
            if not window:
                break
            content = " ".join(word for word, _ in window)
            chunks.append(
                Chunk(
                    section=section,
                    page_number=window[0][1],
                    chunk_index=chunk_index,
                    content=content,
                )
            )
            chunk_index += 1
            start += step

    return chunks
