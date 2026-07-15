import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import ask, health, ingest, memory
from app.api.deps import close_store, get_embeddings, get_tts, init_store
from app.core.timing import TimingMiddleware

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_store()
    # Load TTS + embedding models in the background so the first request
    # doesn't pay for them
    threading.Thread(target=get_tts().warm_up, daemon=True).start()
    threading.Thread(target=get_embeddings().warm_up, daemon=True).start()
    yield
    await close_store()


app = FastAPI(title="Lens", version="0.1.0", lifespan=lifespan)
app.add_middleware(TimingMiddleware)
app.include_router(health.router)
app.include_router(ask.router)
app.include_router(ingest.router)
app.include_router(memory.router)
