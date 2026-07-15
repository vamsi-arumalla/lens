import asyncio
import io
from types import SimpleNamespace

import pytest
from PIL import Image

from app.api.ask import sentence_chunks
from app.core.images import downscale_jpeg
from app.services.vlm import AnthropicVLM
from tests.conftest import make_jpeg


def test_downscale_caps_longest_edge():
    big = make_jpeg(3000, 2000)
    out = downscale_jpeg(big, 1280)
    img = Image.open(io.BytesIO(out))
    assert max(img.size) == 1280
    assert img.format == "JPEG"


def test_downscale_leaves_small_images_alone():
    out = downscale_jpeg(make_jpeg(640, 480), 1280)
    assert Image.open(io.BytesIO(out)).size == (640, 480)


async def _collect(tokens):
    async def gen():
        for t in tokens:
            yield t

    return [s async for s in sentence_chunks(gen())]


@pytest.mark.anyio
async def test_sentence_chunks_splits_on_sentences():
    chunks = await _collect(["The mug is red. ", "It sits on a ", "wooden table."])
    assert chunks == ["The mug is red.", "It sits on a wooden table."]


@pytest.mark.anyio
async def test_sentence_chunks_flushes_trailing_text():
    assert await _collect(["no punctuation at all"]) == ["no punctuation at all"]


@pytest.mark.anyio
async def test_markdown_is_stripped_before_tts():
    assert await _collect(["This is a **Toyota** key `fob`."]) == [
        "This is a Toyota key fob."
    ]


@pytest.mark.anyio
async def test_first_chunk_splits_early_at_clause_boundary():
    # One long sentence: the first chunk should break at the comma so TTS can
    # start before the sentence finishes.
    chunks = await _collect(
        ["Yes, there are several metal items visible here, ",
         "including the key fob and the chain attached to it."]
    )
    assert len(chunks) == 2
    assert chunks[0] == "Yes, there are several metal items visible here,"


class StubStream:
    def __init__(self, delay: float, tokens: list[str]):
        self._delay = delay
        self._tokens = tokens
        self.exited = False

    @property
    def text_stream(self):
        async def gen():
            await asyncio.sleep(self._delay)
            for t in self._tokens:
                yield t

        return gen()

    async def get_final_message(self):
        return SimpleNamespace(stop_reason="end_turn", content=[])


class StubStreamManager:
    def __init__(self, stream: StubStream):
        self._stream = stream

    async def __aenter__(self):
        return self._stream

    async def __aexit__(self, *args):
        self._stream.exited = True


def _stub_vlm(streams: list[StubStream], hedge_ms: int) -> AnthropicVLM:
    vlm = AnthropicVLM("test-key", "test-model", hedge_ms=hedge_ms)
    queue = list(streams)
    vlm._client = SimpleNamespace(
        messages=SimpleNamespace(stream=lambda **kw: StubStreamManager(queue.pop(0)))
    )
    return vlm


@pytest.mark.anyio
async def test_hedge_fires_backup_and_streams_from_winner():
    slow = StubStream(delay=0.5, tokens=["slow answer"])
    fast = StubStream(delay=0.0, tokens=["fast ", "answer"])
    vlm = _stub_vlm([slow, fast], hedge_ms=50)
    out = [t async for t in vlm.stream_answer("q", [])]
    assert out == ["fast ", "answer"]
    await asyncio.sleep(0.6)  # let the losing stream finish and be discarded
    assert slow.exited


@pytest.mark.anyio
async def test_no_hedge_when_first_token_is_fast():
    only = StubStream(delay=0.0, tokens=["quick"])
    vlm = _stub_vlm([only], hedge_ms=1000)  # a second request would IndexError
    out = [t async for t in vlm.stream_answer("q", [])]
    assert out == ["quick"]
    assert only.exited


@pytest.fixture
def anyio_backend():
    return "asyncio"
