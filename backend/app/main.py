import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import ask, health
from app.api.deps import get_tts
from app.core.timing import TimingMiddleware

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Load TTS models in the background so the first ask doesn't pay for it
    threading.Thread(target=get_tts().warm_up, daemon=True).start()
    yield


app = FastAPI(title="Lens", version="0.1.0", lifespan=lifespan)
app.add_middleware(TimingMiddleware)
app.include_router(health.router)
app.include_router(ask.router)
