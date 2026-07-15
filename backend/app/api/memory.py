from fastapi import APIRouter, Depends, HTTPException, Response

from app.api.deps import get_embeddings, get_storage, require_api_key, require_store
from app.memory.store import MomentStore
from app.models.schemas import MomentList, MomentOut, SearchRequest
from app.services.embeddings import Embeddings
from app.services.storage import ObjectStore

router = APIRouter(prefix="/memory", dependencies=[Depends(require_api_key)])


@router.post("/search", response_model=MomentList)
async def search(
    body: SearchRequest,
    store: MomentStore = Depends(require_store),
    embedder: Embeddings = Depends(get_embeddings),
) -> MomentList:
    image_query = await embedder.embed_query_for_images(body.query)
    text_query = await embedder.embed_text(body.query)
    rows = await store.search(image_query, text_query, body.limit)
    return MomentList(moments=[MomentOut.from_row(r) for r in rows])


@router.get("/recent", response_model=MomentList)
async def recent(
    limit: int = 60, store: MomentStore = Depends(require_store)
) -> MomentList:
    rows = await store.recent(min(limit, 200))
    return MomentList(moments=[MomentOut.from_row(r) for r in rows])


async def _image(
    moment_id: str, key_field: str, store: MomentStore, storage: ObjectStore
) -> Response:
    row = await store.get(moment_id)
    if row is None:
        raise HTTPException(404, "no such moment")
    return Response(storage.get(row[key_field]), media_type="image/jpeg")


@router.get("/{moment_id}/thumb.jpg")
async def thumb(
    moment_id: str,
    store: MomentStore = Depends(require_store),
    storage: ObjectStore = Depends(get_storage),
) -> Response:
    return await _image(moment_id, "thumb_key", store, storage)


@router.get("/{moment_id}/frame.jpg")
async def frame(
    moment_id: str,
    store: MomentStore = Depends(require_store),
    storage: ObjectStore = Depends(get_storage),
) -> Response:
    return await _image(moment_id, "frame_key", store, storage)


@router.delete("/{moment_id}", status_code=204)
async def delete(
    moment_id: str,
    store: MomentStore = Depends(require_store),
    storage: ObjectStore = Depends(get_storage),
) -> None:
    if not await store.delete(moment_id):
        raise HTTPException(404, "no such moment")
    storage.delete_prefix(f"moments/{moment_id}")


@router.delete("", status_code=200)
async def delete_all(
    store: MomentStore = Depends(require_store),
    storage: ObjectStore = Depends(get_storage),
) -> dict:
    count = await store.delete_all()
    storage.delete_prefix("moments")
    return {"deleted": count}
