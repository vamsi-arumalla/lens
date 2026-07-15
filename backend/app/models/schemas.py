from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    versions: dict[str, str]


class MomentOut(BaseModel):
    id: UUID
    created_at: datetime
    caption: str
    transcript: str
    question: str
    answer: str
    thumb_url: str
    frame_url: str
    score: float | None = None

    @classmethod
    def from_row(cls, row: dict) -> "MomentOut":
        return cls(
            id=row["id"],
            created_at=row["created_at"],
            caption=row["caption"],
            transcript=row["transcript"],
            question=row["question"],
            answer=row["answer"],
            thumb_url=f"/memory/{row['id']}/thumb.jpg",
            frame_url=f"/memory/{row['id']}/frame.jpg",
            score=row.get("score"),
        )


class MomentList(BaseModel):
    moments: list[MomentOut]


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=8, ge=1, le=50)


class IngestResponse(BaseModel):
    id: UUID
    caption: str
