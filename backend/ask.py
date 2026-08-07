"""Terminal CLI for Epic 3's milestone: ask a real question about a real IPO, get a
correct, cited answer — no UI needed yet.

Usage:
    python ask.py --company "Encube Ethicals" What are the key risk factors?
    python ask.py --company "Encube Ethicals"          # prompts for the question
    GEMINI_MODEL=gemini-pro-latest python ask.py --company "..." <question>   # demo polish
"""

from __future__ import annotations

import argparse
import sys

from app import db
from app.answer import generate_answer
from app.retrieval import retrieve


def main() -> None:
    # Windows consoles default to cp1252, which can't encode characters the model's
    # answer text may contain (bullets, en/em dashes, etc.) — force UTF-8 output.
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Ask a question about an indexed IPO's DRHP.")
    parser.add_argument("--company", required=True, help="Company name (partial match is fine)")
    parser.add_argument("question", nargs="*", help="The question. Omit to be prompted.")
    args = parser.parse_args()

    question = " ".join(args.question) if args.question else input("Question: ").strip()
    if not question:
        print("No question given.")
        sys.exit(1)

    conn = db.connect()
    chunks = retrieve(conn, args.company, question)

    if not chunks:
        print(f"No indexed DRHP chunks found for a company matching {args.company!r}.")
        available = db.list_companies(conn)
        if available:
            print("Companies currently indexed:")
            for name in available:
                print(f"  - {name}")
        sys.exit(1)

    print(f"Retrieved {len(chunks)} chunks from: {chunks[0].company}\n")

    result = generate_answer(question, chunks)

    print(f"--- Answer (model: {result.model}) ---")
    print(result.answer)
    print()

    if result.not_mentioned:
        print("(Not mentioned in the retrieved excerpts.)")
        return

    if not result.citations:
        print("(No citations returned.)")
        return

    print("--- Citations ---")
    by_number = {index: chunk for index, chunk in enumerate(chunks, start=1)}
    for citation in result.citations:
        chunk = by_number.get(citation.chunk_number)
        mark = "verified" if citation.verified else "UNVERIFIED"
        location = f"{chunk.section}, page {chunk.page_number}" if chunk else "unknown chunk"
        print(f"  [{mark}] Excerpt {citation.chunk_number} ({location})")
        print(f"    \"{citation.quote}\"")


if __name__ == "__main__":
    main()
