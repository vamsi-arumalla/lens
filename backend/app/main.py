import logging

from fastapi import FastAPI

from app.api import ask, health
from app.core.timing import TimingMiddleware

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
)

app = FastAPI(title="Lens", version="0.1.0")
app.add_middleware(TimingMiddleware)
app.include_router(health.router)
app.include_router(ask.router)
