import io

import pytest
from PIL import Image

from app.api.ask import sentence_chunks
from app.core.images import downscale_jpeg
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


@pytest.fixture
def anyio_backend():
    return "asyncio"
