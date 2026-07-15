from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.api.deps import (
    get_embeddings,
    get_storage,
    get_stt,
    get_vlm,
    require_api_key,
    require_store,
)
from app.core.config import get_settings
from app.memory.ingest import ingest_moment
from app.memory.store import MomentStore
from app.models.schemas import IngestResponse
from app.services.embeddings import Embeddings
from app.services.storage import ObjectStore
from app.services.stt import SpeechToText
from app.services.vlm import VisionLanguageModel

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.post("/ingest", status_code=201, response_model=IngestResponse)
async def ingest(
    request: Request,
    frames: list[UploadFile] = File(...),
    audio: UploadFile | None = File(None),
    text: str | None = Form(None),
    lat: float | None = Form(None),
    lng: float | None = Form(None),
    stt: SpeechToText = Depends(get_stt),
    vlm: VisionLanguageModel = Depends(get_vlm),
    store: MomentStore = Depends(require_store),
    storage: ObjectStore = Depends(get_storage),
    embedder: Embeddings = Depends(get_embeddings),
) -> IngestResponse:
    settings = get_settings()
    timings = request.state.timings
    if len(frames) > settings.max_frames:
        raise HTTPException(422, f"at most {settings.max_frames} frames allowed")

    transcript = (text or "").strip()
    if audio is not None:
        with timings.stage("stt"):
            heard = await stt.transcribe(await audio.read())
        transcript = f"{heard} {transcript}".strip()

    with timings.stage("ingest"):
        result = await ingest_moment(
            frames=[await f.read() for f in frames],
            transcript=transcript,
            lat=lat,
            lng=lng,
            store=store,
            storage=storage,
            embedder=embedder,
            vlm=vlm,
        )
    return IngestResponse(**result)
