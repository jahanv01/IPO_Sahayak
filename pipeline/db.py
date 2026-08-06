"""Postgres (Supabase) access for DRHP documents and their embedded chunks."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector

from chunker import Chunk

_SCHEMA_SQL = (Path(__file__).parent / "sql" / "001_drhp_tables.sql").read_text()


def connect() -> psycopg.Connection:
    # prepare_threshold=None: Supabase's connection-pooling URI (recommended for a
    # short-lived job like this) runs PgBouncer in transaction mode, which doesn't
    # support psycopg's server-side prepared statements.
    return psycopg.connect(os.environ["DATABASE_URL"], prepare_threshold=None)


def ensure_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(_SCHEMA_SQL)
    conn.commit()
    register_vector(conn)  # must come after the extension above actually exists


def already_processed(conn: psycopg.Connection, detail_url: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "select 1 from drhp_documents where sebi_detail_url = %s and status = 'processed'",
            (detail_url,),
        )
        return cur.fetchone() is not None


def start_document(
    conn: psycopg.Connection, company: str, detail_url: str, pdf_url: str, filed_date: str
) -> int:
    """Create (or reset) a document row and return its id.

    Clears any chunks from a previous, incomplete attempt (e.g. a run that crashed
    mid-way) so a retry doesn't leave duplicate rows behind.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into drhp_documents (company, sebi_detail_url, pdf_url, filed_date, status)
            values (%s, %s, %s, %s, 'processing')
            on conflict (sebi_detail_url) do update set status = 'processing'
            returning id
            """,
            (company, detail_url, pdf_url, filed_date),
        )
        document_id = cur.fetchone()[0]
        cur.execute("delete from drhp_chunks where document_id = %s", (document_id,))
    conn.commit()
    return document_id


def store_chunks(
    conn: psycopg.Connection,
    document_id: int,
    chunks: list[Chunk],
    embeddings: list[list[float]],
) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            """
            insert into drhp_chunks
                (document_id, section, page_number, chunk_index, content, embedding)
            values (%s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    document_id,
                    chunk.section,
                    chunk.page_number,
                    chunk.chunk_index,
                    chunk.content,
                    embedding,
                )
                for chunk, embedding in zip(chunks, embeddings)
            ],
        )
    conn.commit()


def mark_processed(conn: psycopg.Connection, document_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("update drhp_documents set status = 'processed' where id = %s", (document_id,))
    conn.commit()


def mark_failed(conn: psycopg.Connection, document_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("update drhp_documents set status = 'failed' where id = %s", (document_id,))
    conn.commit()
