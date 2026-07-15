import logging
from uuid import uuid4

from app.core.config import get_settings
from app.core.images import downscale_jpeg
from app.memory.store import MomentStore
from app.services.embeddings import Embeddings
from app.services.storage import ObjectStore
from app.services.vlm import VisionLanguageModel

logger = logging.getLogger("lens.ingest")


async def ingest_moment(
    *,
    frames: list[bytes],
    transcript: str = "",
    question: str = "",
    answer: str = "",
    lat: float | None = None,
    lng: float | None = None,
    store: MomentStore,
    storage: ObjectStore,
    embedder: Embeddings,
    vlm: VisionLanguageModel,
) -> dict:
    """Store one moment: frame + thumb to object storage, VLM caption,
    CLIP image embedding + MiniLM text embedding, row in pgvector."""
    settings = get_settings()
    moment_id = str(uuid4())
    frame = downscale_jpeg(frames[0], settings.max_image_edge)
    thumb = downscale_jpeg(frames[0], settings.thumb_edge)

    caption = await vlm.caption([frame])
    text = " ".join(part for part in (caption, transcript, question, answer) if part)
    image_emb = await embedder.embed_image(frame)
    text_emb = await embedder.embed_text(text)

    frame_key = f"moments/{moment_id}/frame.jpg"
    thumb_key = f"moments/{moment_id}/thumb.jpg"
    storage.put(frame_key, frame)
    storage.put(thumb_key, thumb)
    await store.add(
        moment_id=moment_id,
        frame_key=frame_key,
        thumb_key=thumb_key,
        caption=caption,
        transcript=transcript,
        question=question,
        answer=answer,
        lat=lat,
        lng=lng,
        image_emb=image_emb,
        text_emb=text_emb,
    )
    logger.info("moment %s ingested: %r", moment_id, caption)
    return {"id": moment_id, "caption": caption}


async def ingest_moment_safely(**kwargs) -> None:
    """Background-task variant: never lets an ingest failure surface."""
    try:
        await ingest_moment(**kwargs)
    except Exception:
        logger.exception("background moment ingest failed")
