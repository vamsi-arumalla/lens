from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="LENS_", extra="ignore"
    )

    api_key: str = "dev-key"
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    vlm_model: str = "claude-sonnet-4-6"
    vlm_max_tokens: int = 150
    vlm_hedge_ms: int = 1800  # 0 disables first-token hedging
    tts_provider: str = "openai"  # "openai" | "kokoro" (local, no round-trip)
    tts_model: str = "tts-1"
    tts_voice: str = "alloy"
    kokoro_voice: str = "af_heart"
    kokoro_device: str = "auto"  # auto | cpu | mps
    whisper_model: str = "base"
    stt_language: str = "en"  # empty string = auto-detect
    max_image_edge: int = 1280
    max_frames: int = 3

    # Phase 2 — memory. Empty database_url disables memory entirely.
    database_url: str = "postgresql://lens:lens@localhost:5433/lens"
    storage_dir: str = "./data"
    caption_model: str = "claude-haiku-4-5-20251001"
    clip_model: str = "ViT-B-32"
    clip_pretrained: str = "laion2b_s34b_b79k"
    text_embedding_model: str = "all-MiniLM-L6-v2"
    thumb_edge: int = 320


@lru_cache
def get_settings() -> Settings:
    return Settings()
