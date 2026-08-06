# IPO Sahayak

An AI-native DRHP research and IPO education assistant for first-time Indian investors — reads long IPO
prospectus documents and answers investor questions in plain language, always citing the source section.

## Repo structure

```
/frontend      -> React app
/backend       -> Python + FastAPI app
/infra         -> Terraform/OpenTofu code for AWS
/pipeline      -> DRHP scraper + parser scripts
/.github/workflows -> CI/CD pipeline files
```

Work in progress — built epic by epic via feature branches and PRs into `main`.

## Progress

### Epic 1: Cloud Foundation + CI/CD Skeleton — 🟢 Done
Hello-world backend + frontend, CI/CD workflows, and Render config — merged and live.

- Backend: FastAPI, Docker, pytest, ruff
- Frontend: Vite/React, pings backend `/health`
- 3 GitHub Actions workflows (backend, frontend, scraper), read-only permissions
- CORS restricted via env var, Docker runs as non-root

**Done (manual, not code):**
- [✓] Create Supabase project, enable `pgvector`
- [✓] Connect repo to Render (`/backend`) and Vercel (`/frontend`)
- [✓] Set `ALLOWED_ORIGINS` in Render once the Vercel URL is known

### Epic 2: Data Pipeline (DRHP Scraper + Parser) — 🟢 Done
Real DRHP scraper — fetches filings from SEBI, extracts and section-chunks their text,
embeds each chunk for free, and stores everything in Supabase/pgvector. Merged, running
on the existing twice-daily schedule, and verified against live data.

- `sebi_client.py`: fetches SEBI's public issues listing, resolves each filing's real PDF
  (embedded in an iframe, separate from the "Abridged Prospectus" link in the row text)
- `pdf_extractor.py`: per-page text via PyMuPDF
- `chunker.py`: tags pages into 4 sections (Risk Factors, Business, Financials, Objects
  of Issue) via a heading heuristic, then splits into overlapping ~150-word chunks
- `embedder.py`: free local embeddings (`fastembed` + all-MiniLM-L6-v2, $0 cost)
- `db.py`: stores documents/chunks in Supabase; skips already-processed filings so the
  scheduled job naturally picks up new IPOs over time; caps each run to 3 new filings
- `pipeline.yml` CI (lint+test); `scraper.yml` now uses `DATABASE_URL` instead of the
  unused Supabase REST vars left over from the Epic 1 stub

**Validated against real data:** ran end-to-end against a live 503-page DRHP before
merging, which caught and fixed two real bugs — the actual SEBI heading format is
prefixed ("SECTION II: RISK FACTORS", not bare), and a naive `startswith` check was a
false positive on body prose ("Our business is dependent upon..." starts with "OUR
BUSINESS"). Since merge, the scheduled runs have processed **5 real IPOs, 7,000 chunks,
all 4 sections detected on every document** (Advanced Sys Tek, Encube Ethicals, Indian
Gas Exchange, Veritas Finance, Yogiji Digi).

**Done (manual, not code):**
- [✓] Add `DATABASE_URL` (Supabase **Transaction pooler** URI — the direct-connection
  URI is IPv6-only and unreachable from GitHub Actions runners) as a GitHub Actions secret
- [✓] Rotate the Supabase DB password after an unencoded `@` in it caused a URL
  mis-parse that leaked a password fragment into a workflow log
