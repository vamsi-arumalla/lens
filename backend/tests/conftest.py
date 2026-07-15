import io
import os
from collections.abc import AsyncIterator

# Env vars beat the .env file in pydantic-settings, so tests stay hermetic
# even when backend/.env holds real keys or a local TTS provider (whose
# warm-up would otherwise download models during tests).
os.environ["LENS_API_KEY"] = "dev-key"
os.environ["LENS_TTS_PROVIDER"] = "openai"
os.environ["LENS_DATABASE_URL"] = ""  # memory off unless a test wires a fake

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.deps import (
    get_embeddings,
    get_storage,
    get_store,
    get_stt,
    get_tts,
    get_vlm,
    require_store,
)
from app.main import app
from app.services.embeddings import IMAGE_DIM, TEXT_DIM, Embeddings
from app.services.storage import LocalDiskStore
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
        self.memory_search = None

    async def stream_answer(
        self, question: str, images_jpeg: list[bytes], memory_search=None
    ) -> AsyncIterator[str]:
        self.calls.append((question, len(images_jpeg)))
        self.memory_search = memory_search
        for t in self.tokens:
            yield t

    async def caption(self, images_jpeg: list[bytes]) -> str:
        return "a red mug on a table"


class FailingVLM(VisionLanguageModel):
    async def stream_answer(
        self, question, images_jpeg, memory_search=None
    ) -> AsyncIterator[str]:
        raise RuntimeError("vlm down")
        yield  # pragma: no cover

    async def caption(self, images_jpeg: list[bytes]) -> str:
        raise RuntimeError("vlm down")


class FakeTTS(TextToSpeech):
    """Echoes the text back as bytes so tests can assert what was spoken."""

    async def stream_speech(self, text: str) -> AsyncIterator[bytes]:
        yield f"[{text}]".encode()


class FakeEmbeddings(Embeddings):
    async def embed_image(self, jpeg: bytes) -> list[float]:
        return [0.1] * IMAGE_DIM

    async def embed_text(self, text: str) -> list[float]:
        return [0.2] * TEXT_DIM

    async def embed_query_for_images(self, text: str) -> list[float]:
        return [0.1] * IMAGE_DIM


class FakeStore:
    """In-memory stand-in for MomentStore; search returns newest-first."""

    def __init__(self):
        self.rows: dict[str, dict] = {}

    async def add(self, *, moment_id, **fields):
        from datetime import UTC, datetime

        self.rows[moment_id] = {
            "id": moment_id,
            "created_at": datetime.now(UTC),
            **fields,
        }

    async def recent(self, limit=60):
        rows = sorted(self.rows.values(), key=lambda r: r["created_at"], reverse=True)
        return rows[:limit]

    async def get(self, moment_id):
        return self.rows.get(moment_id)

    async def search(self, image_query_emb, text_query_emb, k=8):
        return [{**r, "score": 0.9} for r in (await self.recent(k))]

    async def delete(self, moment_id):
        return self.rows.pop(moment_id, None) is not None

    async def delete_all(self):
        n = len(self.rows)
        self.rows.clear()
        return n


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


@pytest.fixture
def fake_store() -> FakeStore:
    return FakeStore()


@pytest.fixture
def memory_client(fake_vlm: FakeVLM, fake_store: FakeStore, tmp_path):
    """Client with the full memory stack faked (store, embeddings, disk)."""
    app.dependency_overrides[get_stt] = lambda: FakeSTT()
    app.dependency_overrides[get_vlm] = lambda: fake_vlm
    app.dependency_overrides[get_tts] = lambda: FakeTTS()
    app.dependency_overrides[get_embeddings] = lambda: FakeEmbeddings()
    app.dependency_overrides[get_storage] = lambda: LocalDiskStore(str(tmp_path))
    app.dependency_overrides[get_store] = lambda: fake_store
    app.dependency_overrides[require_store] = lambda: fake_store
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_jpeg(width: int = 64, height: int = 64) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), "red").save(buf, "JPEG")
    return buf.getvalue()
