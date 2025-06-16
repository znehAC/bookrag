from typing import List, Tuple

import numpy as np
import psycopg2

from config import settings

POSTGRES_URL = settings.POSTGRES_URL

TABLE_DDL = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS chunks (
  id SERIAL PRIMARY KEY,
  text TEXT NOT NULL,
  embedding VECTOR(384)
);
"""


def _to_pgvec(vec) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


def init_db() -> None:
    with psycopg2.connect(settings.POSTGRES_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(TABLE_DDL)


class PgVectorStore:
    def __init__(self, dsn: str = POSTGRES_URL) -> None:
        self.conn = psycopg2.connect(dsn)
        self.conn.autocommit = True
        with self.conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(TABLE_DDL)

    def add(self, texts: List[str], embeds: "np.ndarray") -> None:
        assert embeds.shape[0] == len(texts)
        with self.conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO chunks (text, embedding) VALUES (%s, %s)",
                [(t, e.tolist()) for t, e in zip(texts, embeds)],
            )

    def search(self, query_embed: "np.ndarray", k: int = 3):
        vec_str = _to_pgvec(query_embed[0])
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT text,
                    embedding <#> %s::vector AS score
                FROM   chunks
                ORDER  BY embedding <#> %s::vector
                LIMIT  %s;
                """,
                (vec_str, vec_str, k),
            )
            return [(row[0], float(row[1])) for row in cur.fetchall()]
