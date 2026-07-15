from functools import lru_cache

from fastapi import Header, HTTPException

from app.core.config import get_settings
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
    return AnthropicVLM(s.anthropic_api_key, s.vlm_model, s.vlm_max_tokens)


@lru_cache
def get_tts() -> TextToSpeech:
    s = get_settings()
    if s.tts_provider == "kokoro":
        return KokoroTTS(s.kokoro_voice)
    return OpenAITTS(s.openai_api_key, s.tts_model, s.tts_voice)
