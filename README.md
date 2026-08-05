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

### Epic 1: Cloud Foundation + CI/CD Skeleton — 🟡 Code done, deployment pending
Hello-world backend + frontend, CI/CD workflows, and Render config — merged.
Live deployment blocked on connecting Render/Vercel to the repo (manual step).

- Backend: FastAPI, Docker, pytest, ruff
- Frontend: Vite/React, pings backend `/health`
- 3 GitHub Actions workflows (backend, frontend, scraper), read-only permissions
- CORS restricted via env var, Docker runs as non-root

**Pending (manual, not code):**
- [ ] Create Supabase project, enable `pgvector`
- [ ] Connect repo to Render (`/backend`) and Vercel (`/frontend`)
- [ ] Set `ALLOWED_ORIGINS` in Render once the Vercel URL is known
