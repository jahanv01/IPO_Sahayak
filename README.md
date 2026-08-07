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

### Epic 3: AI / Search Engine — 🟢 Done
Given a question, return a grounded, cited answer. Two-stage retrieval (pgvector search
+ cross-encoder re-rank) feeds a handful of the most relevant DRHP excerpts to an LLM
under a strict grounding prompt, and every citation it returns is checked against the
source text before being shown.

- `app/embeddings.py`: query embeddings via the same free local model the pipeline
  indexed chunks with (`fastembed` + all-MiniLM-L6-v2) — duplicated from
  `pipeline/embedder.py` rather than imported, since Render's Docker build context for
  `/backend` can't see outside that directory
- `app/reranker.py`: cross-encoder re-ranking (`fastembed` + `Xenova/ms-marco-MiniLM-L-6-v2`)
- `app/retrieval.py`: embeds the question, pulls the top 10 candidates from pgvector, then
  re-ranks down to the best 5 — better input, less work for the model to sift through
- `app/answer.py`: sends the question + top 5 chunks to Gemini with a strict grounding
  prompt (answer only from the given excerpts, cite the section/page, say "not mentioned"
  if it isn't there), a RAFT-style instruction that some excerpts may be irrelevant
  distractors to ignore, and a safety rule to never give buy/sell advice — then a local,
  deterministic `verify_citations()` check confirms each cited quote actually appears in
  its source chunk before the answer is shown
- `ask.py`: terminal CLI — `python ask.py --company "..." <question>` — the epic's
  milestone deliverable
- Model: **Gemini free tier** (`gemini-flash-latest` for dev/testing, `gemini-pro-latest`
  for demo polish via `GEMINI_MODEL`) rather than a paid API — no billing needed to build
  or test this epic. `generate_answer(question, chunks)` keeps a stable signature so the
  model/provider behind it can be swapped later without touching retrieval or the CLI.
- Tests mock the Gemini client entirely — no real API calls or DB connections in CI

**Validated against real data:** ran 10 real questions against 5 of the indexed DRHPs
(Encube Ethicals, Advanced Sys Tek, Veritas Finance, Indian Gas Exchange, Yogiji Digi) —
business summaries, risk factors, and specific financial figures (e.g. R&D spend as %
of revenue by fiscal year) all came back correct with every citation verified against
the source chunk. Also confirmed the model gives an honest partial answer instead of
fabricating when only part of a question is covered (dividend history), and correctly
refuses to give investment advice on a "should I buy this IPO" probe while still citing
what the document itself says about relying on your own judgment.

**Bugs found and fixed along the way:**
- pgvector's `<=>` operator needs an explicit `::vector` cast on the query parameter in
  a raw `SELECT` — unlike an `INSERT`, there's no target column to infer the type from
- `gemini-2.5-flash`, the model current at the time this was written, already 404s as
  "no longer available to new users" — switched to the `-latest` aliases
  (`gemini-flash-latest` / `gemini-pro-latest`) so the code isn't pinned to a dated model
- `ask.py`'s citation markers crashed on Windows' default `cp1252` console encoding —
  switched to ASCII markers and forced UTF-8 stdout

**Done (manual, not code):**
- [✓] Create a free Gemini API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
