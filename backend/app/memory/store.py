from typing import Any

import asyncpg
import numpy as np
from pgvector.asyncpg import register_vector

from app.services.embeddings import IMAGE_DIM, TEXT_DIM

_SCHEMA = f"""
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS moments (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    frame_key TEXT NOT NULL,
    thumb_key TEXT NOT NULL,
    caption TEXT NOT NULL DEFAULT '',
    transcript TEXT NOT NULL DEFAULT '',
    question TEXT NOT NULL DEFAULT '',
    answer TEXT NOT NULL DEFAULT '',
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    image_emb vector({IMAGE_DIM}) NOT NULL,
    text_emb vector({TEXT_DIM}) NOT NULL
);
CREATE INDEX IF NOT EXISTS moments_created_idx ON moments (created_at DESC);
"""

_ROW_COLS = (
    "id, created_at, frame_key, thumb_key, caption, transcript, question, answer, lat, lng"
)

# Hybrid score: image similarity + text similarity + a boost that halves
# roughly weekly, so "the whiteboard from this morning" beats one from a month
# ago at equal similarity.
_SEARCH_SQL = f"""
SELECT {_ROW_COLS},
       (0.45 * (1 - (image_emb <=> $1))
      + 0.45 * (1 - (text_emb <=> $2))
      + 0.10 / (1.0 + EXTRACT(EPOCH FROM (now() - created_at)) / 604800.0)) AS score
FROM moments
ORDER BY score DESC
LIMIT $3
"""


class MomentStore:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        # The vector extension must exist before register_vector can
        # introspect the type, so bootstrap with a plain connection first.
        conn = await asyncpg.connect(self._dsn)
        try:
            await conn.execute(_SCHEMA)
        finally:
            await conn.close()
        self._pool = await asyncpg.create_pool(
            self._dsn, init=register_vector, min_size=1, max_size=5
        )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def add(
        self,
        *,
        moment_id: str,
        frame_key: str,
        thumb_key: str,
        caption: str,
        transcript: str,
        question: str,
        answer: str,
        lat: float | None,
        lng: float | None,
        image_emb: list[float],
        text_emb: list[float],
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO moments (id, frame_key, thumb_key, caption, transcript,
                                     question, answer, lat, lng, image_emb, text_emb)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                moment_id,
                frame_key,
                thumb_key,
                caption,
                transcript,
                question,
                answer,
                lat,
                lng,
                np.asarray(image_emb, dtype=np.float32),
                np.asarray(text_emb, dtype=np.float32),
            )

    async def recent(self, limit: int = 60) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT {_ROW_COLS} FROM moments ORDER BY created_at DESC LIMIT $1",
                limit,
            )
        return [dict(r) for r in rows]

    async def get(self, moment_id: str) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT {_ROW_COLS} FROM moments WHERE id = $1", moment_id
            )
        return dict(row) if row else None

    async def search(
        self, image_query_emb: list[float], text_query_emb: list[float], k: int = 8
    ) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                _SEARCH_SQL,
                np.asarray(image_query_emb, dtype=np.float32),
                np.asarray(text_query_emb, dtype=np.float32),
                k,
            )
        return [dict(r) for r in rows]

    async def delete(self, moment_id: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute("DELETE FROM moments WHERE id = $1", moment_id)
        return result.endswith("1")

    async def delete_all(self) -> int:
        async with self._pool.acquire() as conn:
            result = await conn.execute("DELETE FROM moments")
        return int(result.split()[-1])
