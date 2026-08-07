"""Read-only Postgres (Supabase/pgvector) access for retrieval.

Separate from the pipeline's db.py, which owns writes and schema — this module only
ever reads drhp_documents/drhp_chunks (written by pipeline/scraper.py in Epic 2).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg
from pgvector.psycopg import register_vector


@dataclass
class RetrievedChunk:
    chunk_id: int
    company: str
    section: str
    page_number: int | None
    content: str
    distance: float


def connect() -> psycopg.Connection:
    # prepare_threshold=None: Supabase's pooled connection runs PgBouncer in
    # transaction mode, which doesn't support psycopg's server-side prepared statements.
    conn = psycopg.connect(os.environ["DATABASE_URL"], prepare_threshold=None)
    register_vector(conn)
    return conn


def fetch_candidates(
    conn: psycopg.Connection, company: str, query_embedding: list[float], limit: int
) -> list[RetrievedChunk]:
    """Nearest-neighbor search over one company's processed chunks, closest first."""
    with conn.cursor() as cur:
        cur.execute(
            """
            select c.id, d.company, c.section, c.page_number, c.content,
                   c.embedding <=> %(embedding)s::vector as distance
            from drhp_chunks c
            join drhp_documents d on d.id = c.document_id
            where d.company ilike %(company)s and d.status = 'processed'
            order by c.embedding <=> %(embedding)s::vector
            limit %(limit)s
            """,
            {"embedding": query_embedding, "company": f"%{company}%", "limit": limit},
        )
        rows = cur.fetchall()
    return [
        RetrievedChunk(
            chunk_id=row[0],
            company=row[1],
            section=row[2],
            page_number=row[3],
            content=row[4],
            distance=row[5],
        )
        for row in rows
    ]


def list_companies(conn: psycopg.Connection) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            "select distinct company from drhp_documents "
            "where status = 'processed' order by company"
        )
        return [row[0] for row in cur.fetchall()]
