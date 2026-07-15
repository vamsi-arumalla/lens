from functools import lru_cache

from fastapi import Header, HTTPException

from app.core.config import get_settings
from app.memory.store import MomentStore
from app.services.embeddings import Embeddings, LocalEmbeddings
from app.services.storage import LocalDiskStore, ObjectStore
from app.services.stt import FasterWhisperSTT, SpeechToText
from app.services.tts import KokoroTTS, OpenAITTS, TextToSpeech
from app.services.vlm import AnthropicVLM, VisionLanguageModel


async def require_api_key(x_api_key: str = Header(default="")) -> None:
    if x_api_key != get_settings().api_key:
        raise HTTPException(status_code=401, detail="invalid API key")


@lru_cache
def get_stt() -> SpeechToText:
    return FasterWhisperSTT(get_settings().whisper_model)


@lru_cache
def get_vlm() -> VisionLanguageModel:
    s = get_settings()
    return AnthropicVLM(
        s.anthropic_api_key, s.vlm_model, s.vlm_max_tokens, s.caption_model
    )


@lru_cache
def get_storage() -> ObjectStore:
    return LocalDiskStore(get_settings().storage_dir)


@lru_cache
def get_embeddings() -> Embeddings:
    s = get_settings()
    return LocalEmbeddings(s.clip_model, s.clip_pretrained, s.text_embedding_model)


# Created/connected by the lifespan hook; None when memory is disabled
_store: MomentStore | None = None


async def init_store() -> MomentStore | None:
    global _store
    dsn = get_settings().database_url
    if dsn:
        _store = MomentStore(dsn)
        await _store.connect()
    return _store


async def close_store() -> None:
    global _store
    if _store is not None:
        await _store.close()
        _store = None


def get_store() -> MomentStore | None:
    return _store


def require_store() -> MomentStore:
    if _store is None:
        raise HTTPException(503, "memory is disabled: no database configured")
    return _store


@lru_cache
def get_tts() -> TextToSpeech:
    s = get_settings()
    if s.tts_provider == "kokoro":
        return KokoroTTS(s.kokoro_voice)
    return OpenAITTS(s.openai_api_key, s.tts_model, s.tts_voice)
