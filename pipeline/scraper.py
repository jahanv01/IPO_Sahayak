"""DRHP scraper entry point.

Fetches recent DRHP filings from SEBI, downloads a handful of new ones, extracts and
section-chunks their text, embeds each chunk with a free local model, and stores
everything in Supabase (Postgres + pgvector). Safe to run repeatedly on a schedule:
already-processed filings are skipped via drhp_documents.sebi_detail_url, so later runs
naturally pick up only what's new.
"""

from __future__ import annotations

import requests

import db
import sebi_client
from chunker import build_chunks, detect_sections
from embedder import embed_texts
from pdf_extractor import extract_pages

# Keep each run small on purpose — this is a $0 GitHub Actions job, not a bulk backfill.
MAX_NEW_FILINGS_PER_RUN = 3


def process_filing(conn, session: requests.Session, filing: sebi_client.DrhpFiling) -> bool:
    print(f"Processing: {filing.company} ({filing.filed_date})")

    pdf_url = sebi_client.fetch_pdf_url(session, filing.detail_url)
    if pdf_url is None:
        print(f"  Skipping — no PDF link found on {filing.detail_url}")
        return False

    document_id = db.start_document(
        conn, filing.company, filing.detail_url, pdf_url, filing.filed_date
    )

    try:
        pdf_bytes = sebi_client.download_pdf(session, pdf_url)
        pages = extract_pages(pdf_bytes)
        print(f"  Extracted {len(pages)} pages")

        sectioned_pages = detect_sections(pages)
        chunks = build_chunks(sectioned_pages)
        sections_found = sorted({page.section for page in sectioned_pages})
        print(f"  Built {len(chunks)} chunks across sections: {sections_found or 'none detected'}")

        if chunks:
            embeddings = embed_texts([chunk.content for chunk in chunks])
            db.store_chunks(conn, document_id, chunks, embeddings)

        db.mark_processed(conn, document_id)
        print(f"  Done: {filing.company}")
        return True
    except Exception as exc:  # noqa: BLE001 - one bad filing shouldn't kill the whole run
        print(f"  FAILED: {filing.company}: {exc}")
        db.mark_failed(conn, document_id)
        return False


def main() -> None:
    conn = db.connect()
    db.ensure_schema(conn)

    session = requests.Session()
    filings = sebi_client.fetch_listing(session)
    print(f"Found {len(filings)} candidate DRHP filings on SEBI's listing page")

    new_filings = [
        filing for filing in filings if not db.already_processed(conn, filing.detail_url)
    ]
    print(f"{len(new_filings)} not yet processed")

    to_process = new_filings[:MAX_NEW_FILINGS_PER_RUN]
    if not to_process:
        print("Nothing new to process this run.")
        return

    processed_count = sum(process_filing(conn, session, filing) for filing in to_process)
    print(f"Run complete: {processed_count}/{len(to_process)} filings processed successfully")


if __name__ == "__main__":
    main()
