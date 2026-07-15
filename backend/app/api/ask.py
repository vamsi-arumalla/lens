import logging
import re
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.api.deps import get_stt, get_tts, get_vlm, require_api_key
from app.core.config import get_settings
from app.core.images import downscale_jpeg
from app.services.stt import SpeechToText
from app.services.tts import TextToSpeech
from app.services.vlm import VisionLanguageModel

logger = logging.getLogger("lens.ask")

router = APIRouter(dependencies=[Depends(require_api_key)])

FALLBACK_MESSAGE = "Sorry, I couldn't process that."

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_CLAUSE_END = re.compile(r"(?<=[,;:])\s+")
_EARLY_SPLIT_MIN = 15
# The model sometimes emits markdown despite the prompt; strip it before TTS
_TTS_UNSPEAKABLE = re.compile(r"[*_#`]+")


async def sentence_chunks(text_stream: AsyncIterator[str]) -> AsyncIterator[str]:
    """Regroup a token stream into sentence-sized chunks so TTS can start
    speaking before the full answer is generated. The first chunk may split at
    a clause boundary: time-to-first-audio matters more than prosody there."""
    buffer = ""
    yielded_any = False
    async for token in text_stream:
        buffer += _TTS_UNSPEAKABLE.sub("", token)
        parts = _SENTENCE_END.split(buffer)
        while len(parts) > 1:
            sentence = parts.pop(0)
            if sentence:
                yield sentence
                yielded_any = True
        buffer = parts[0]
        if not yielded_any and len(buffer) >= 2 * _EARLY_SPLIT_MIN:
            for m in _CLAUSE_END.finditer(buffer):
                if m.start() >= _EARLY_SPLIT_MIN:
                    yield buffer[: m.start()]
                    yielded_any = True
                    buffer = buffer[m.end():]
                    break
    if buffer.strip():
        yield buffer.strip()


@router.post("/ask")
async def ask(
    request: Request,
    frames: list[UploadFile] = File(...),
    audio: UploadFile | None = File(None),
    text: str | None = Form(None),
    stt: SpeechToText = Depends(get_stt),
    vlm: VisionLanguageModel = Depends(get_vlm),
    tts: TextToSpeech = Depends(get_tts),
) -> StreamingResponse:
    settings = get_settings()
    timings = request.state.timings

    if len(frames) > settings.max_frames:
        raise HTTPException(422, f"at most {settings.max_frames} frames allowed")

    with timings.stage("image_prep"):
        images = [
            downscale_jpeg(await f.read(), settings.max_image_edge) for f in frames
        ]

    question = (text or "").strip()
    if audio is not None:
        with timings.stage("stt"):
            transcript = await stt.transcribe(await audio.read())
        question = f"{transcript} {question}".strip()
    if not question:
        raise HTTPException(422, "no question: provide audio or text")
    logger.info("question: %r", question)

    # Get the first VLM token before opening the stream so a dead VLM becomes
    # a spoken fallback instead of a broken audio stream (spec: no raw 500 on
    # the user path).
    text_stream = vlm.stream_answer(question, images)
    try:
        first_token = await anext(text_stream)
        timings.mark("vlm_first_token")
    except StopAsyncIteration:
        first_token = ""
        timings.mark("vlm_first_token")
    except Exception:
        logger.exception("VLM failed for question %r", question)
        return StreamingResponse(
            _speak_fallback(tts),
            media_type="audio/mpeg",
            headers={"X-Lens-Error": "vlm_failed"},
        )

    async def _resume() -> AsyncIterator[str]:
        yield first_token
        async for token in text_stream:
            yield token
        timings.mark("vlm_total")

    async def _audio_stream() -> AsyncIterator[bytes]:
        got_first_byte = False
        spoken: list[str] = []
        try:
            async for sentence in sentence_chunks(_resume()):
                spoken.append(sentence)
                async for chunk in tts.stream_speech(sentence):
                    if not got_first_byte:
                        timings.mark("tts_first_byte")
                        got_first_byte = True
                    yield chunk
        except Exception:
            # Headers are already sent; all we can do is end the stream.
            logger.exception("streaming failed mid-answer")
        finally:
            logger.info("answer: %r", " ".join(spoken))
            timings.finish()

    return StreamingResponse(_audio_stream(), media_type="audio/mpeg")


async def _speak_fallback(tts: TextToSpeech) -> AsyncIterator[bytes]:
    try:
        async for chunk in tts.stream_speech(FALLBACK_MESSAGE):
            yield chunk
    except Exception:
        logger.exception("TTS failed while speaking the fallback message")
