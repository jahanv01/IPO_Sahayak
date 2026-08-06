"""Extracts per-page text from a DRHP PDF."""

from __future__ import annotations

import fitz  # PyMuPDF


def extract_pages(pdf_bytes: bytes) -> list[str]:
    """Return the plain text of each page, in order (index 0 = page 1)."""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        return [page.get_text() for page in doc]
