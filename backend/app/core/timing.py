import logging
import time
from contextlib import contextmanager

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("lens.timing")


class StageTimings:
    """Collects per-stage millisecond timings for one request.

    For streaming responses the header is written when streaming starts, so it
    carries only the stages measured up to that point (stt_ms,
    vlm_first_token_ms). The complete set including tts_first_byte_ms and
    total_ms is logged when the stream finishes.
    """

    def __init__(self) -> None:
        self._start = time.perf_counter()
        self.stages: dict[str, int] = {}

    @contextmanager
    def stage(self, name: str):
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self.stages[f"{name}_ms"] = round((time.perf_counter() - t0) * 1000)

    def mark(self, name: str) -> None:
        """Record elapsed time since request start under `name`."""
        self.stages[f"{name}_ms"] = round((time.perf_counter() - self._start) * 1000)

    def finish(self) -> None:
        self.mark("total")
        logger.info("stage timings: %s", self.header())

    def header(self) -> str:
        return ",".join(f"{k}={v}" for k, v in self.stages.items())


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        timings = StageTimings()
        request.state.timings = timings
        response = await call_next(request)
        if not timings.stages:
            timings.mark("total")
        response.headers["X-Stage-Timings"] = timings.header()
        return response
