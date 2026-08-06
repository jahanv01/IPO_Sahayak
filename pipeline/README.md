# Pipeline

DRHP scraper — pulls fresh prospectus filings from SEBI, extracts and section-chunks their
text, embeds each chunk with a free local model, and stores everything in Supabase
(Postgres + pgvector). Runs on a schedule via `.github/workflows/scraper.yml`.

## How it works

1. `sebi_client.py` — fetches SEBI's public issues listing and resolves each filing's
   real DRHP PDF URL (embedded in an iframe on the filing's detail page).
2. `pdf_extractor.py` — extracts per-page text with PyMuPDF.
3. `chunker.py` — tags each page with one of four target sections (Risk Factors, Business,
   Financials, Objects of Issue) using a heading heuristic, then splits each section into
   overlapping ~150-word chunks.
4. `embedder.py` — embeds each chunk with `sentence-transformers/all-MiniLM-L6-v2` via
   `fastembed` (runs locally in the Actions job, no API cost).
5. `db.py` — stores documents/chunks in Supabase. Already-processed filings (tracked by
   their SEBI detail URL) are skipped, so repeated scheduled runs only pick up what's new.

Each run processes at most `MAX_NEW_FILINGS_PER_RUN` (3) new filings — this is a $0
GitHub Actions job, not a bulk backfill.

## Local dev

```
python -m venv .venv && source .venv/Scripts/activate  # or .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env  # fill in DATABASE_URL, then `set -a; source .env; set +a`
python scraper.py
pytest -q
```

## Known limitations

- Section detection is a heading heuristic, not a table-of-contents parse — boundaries
  are usually right but not guaranteed exact.
- Financial tables are extracted as plain text (PyMuPDF), so column alignment isn't
  preserved. A table-aware extractor (e.g. `camelot`, `pdfplumber`) would improve this if
  needed later.
- Only the SEBI listing's first page (~25 most recent filings) is scanned — deliberate,
  matches "don't try to index everything yet."
