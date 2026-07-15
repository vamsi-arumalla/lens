import io
import os
from collections.abc import AsyncIterator

# Env vars beat the .env file in pydantic-settings, so tests stay hermetic
# even when backend/.env holds real keys.
os.environ["LENS_API_KEY"] = "dev-key"

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.deps import get_stt, get_tts, get_vlm
from app.main import app
from app.services.stt import SpeechToText
from app.services.tts import TextToSpeech
from app.services.vlm import VisionLanguageModel

API_KEY = "dev-key"  # pinned via the env var above


class FakeSTT(SpeechToText):
    async def transcribe(self, audio: bytes) -> str:
        return "what is this"


class FakeVLM(VisionLanguageModel):
    def __init__(self, tokens: list[str] | None = None):
        self.tokens = tokens if tokens is not None else ["It is ", "a red mug."]
        self.calls: list[tuple[str, int]] = []

    async def stream_answer(
        self, question: str, images_jpeg: list[bytes]
    ) -> AsyncIterator[str]:
        self.calls.append((question, len(images_jpeg)))
        for t in self.tokens:
            yield t


class FailingVLM(VisionLanguageModel):
    async def stream_answer(self, question, images_jpeg) -> AsyncIterator[str]:
        raise RuntimeError("vlm down")
        yield  # pragma: no cover


class FakeTTS(TextToSpeech):
    """Echoes the text back as bytes so tests can assert what was spoken."""

    async def stream_speech(self, text: str) -> AsyncIterator[bytes]:
        yield f"[{text}]".encode()


@pytest.fixture
def fake_vlm() -> FakeVLM:
    return FakeVLM()


@pytest.fixture
def client(fake_vlm: FakeVLM):
    app.dependency_overrides[get_stt] = lambda: FakeSTT()
    app.dependency_overrides[get_vlm] = lambda: fake_vlm
    app.dependency_overrides[get_tts] = lambda: FakeTTS()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def failing_vlm_client():
    app.dependency_overrides[get_stt] = lambda: FakeSTT()
    app.dependency_overrides[get_vlm] = lambda: FailingVLM()
    app.dependency_overrides[get_tts] = lambda: FakeTTS()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_jpeg(width: int = 64, height: int = 64) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), "red").save(buf, "JPEG")
    return buf.getvalue()
