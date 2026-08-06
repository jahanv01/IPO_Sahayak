-- DRHP documents + their embedded, section-chunked text.
-- Applied automatically by db.ensure_schema() on every scraper run, and safe to run
-- by hand in the Supabase SQL editor too (everything is idempotent).

create extension if not exists vector;

create table if not exists drhp_documents (
    id bigint generated always as identity primary key,
    company text not null,
    sebi_detail_url text not null unique,
    pdf_url text not null,
    filed_date text,
    status text not null default 'processing',
    created_at timestamptz not null default now()
);

create table if not exists drhp_chunks (
    id bigint generated always as identity primary key,
    document_id bigint not null references drhp_documents (id) on delete cascade,
    section text not null,
    page_number int,
    chunk_index int not null,
    content text not null,
    embedding vector(384),
    created_at timestamptz not null default now()
);

create index if not exists drhp_chunks_embedding_idx
    on drhp_chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);

create index if not exists drhp_chunks_document_id_idx on drhp_chunks (document_id);

-- Direct Postgres connections (what this scraper uses) run as the table owner and
-- bypass RLS by default, so the scraper's own reads/writes aren't affected by the
-- "auto-enable RLS on new tables" trigger. These tables ARE RLS-enabled for when a
-- later epic exposes them to the frontend via the anon/authenticated PostgREST roles —
-- that epic needs to add explicit policies (e.g. public SELECT) before this data is
-- reachable from the app.
